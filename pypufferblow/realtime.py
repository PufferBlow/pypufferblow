"""
Async client for the Pufferblow command/event protocol (v1).

One websocket carries everything: you send *commands* (``message.create``, ``message.edit``, ...)
and get an acknowledgment once the work is committed, and the server pushes *events*
(``message.created``, ...) for the channels you can see. The client handles the parts that are
easy to get wrong: matching acks to commands, safe retries with an idempotency ``nonce``,
dropping duplicate events, and catching up with ``events.resync`` after a gap or a reconnect.

Example:
    .. code-block:: python

        async with ProtocolClient(auth_token, "https://chat.example.org") as client:
            async for event in client.events():
                if event.name == "message.created" and event.data["content"] == "!ping":
                    await client.create_message(event.channel_id, "pong")
"""

__all__ = ["ProtocolClient"]

import asyncio
import inspect
import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

try:
    import websockets
except ImportError:  # pragma: no cover - the dependency is declared, this only guards odd installs
    websockets = None

from pypufferblow.models.options_model import http_to_websocket_base, normalize_instance
from pypufferblow.protocol import (
    Ack,
    ErrorFrame,
    EventFrame,
    EventTracker,
    Hello,
    ProtocolError,
    ProtocolMessage,
    build_command,
    parse_frame,
)

logger = logging.getLogger("pypufferblow.realtime")

EventCallback = Callable[[EventFrame], "Awaitable[None] | None"]
ResyncCallback = Callable[[str, list[ProtocolMessage]], "Awaitable[None] | None"]

DEFAULT_RESYNC_LIMIT = 50
_CLOSED = object()


class ProtocolClient:
    """A protocol v1 connection that reconnects by itself.

    Args:
        auth_token: User authentication token.
        instance: Instance URL or authority, e.g. ``https://chat.example.org`` or ``localhost:7575``.
        command_timeout: Seconds to wait for an acknowledgment before raising ``TIMEOUT``.
        on_event: Called for every event that has not been seen before (sync or async function).
        on_resync: Called with ``(channel_id, messages)`` after a gap or reconnect, with the
            server's current view of the channel's recent messages.
        reconnect: Reconnect with exponential backoff when the socket drops.
        ping_interval: Seconds between application-level pings (they also re-check the token).
    """

    def __init__(
        self,
        auth_token: str,
        instance: str | None = None,
        *,
        command_timeout: float = 15.0,
        on_event: EventCallback | None = None,
        on_resync: ResyncCallback | None = None,
        reconnect: bool = True,
        ping_interval: float = 30.0,
        max_backoff: float = 30.0,
    ) -> None:
        if websockets is None:  # pragma: no cover
            raise ImportError("websockets package is required for WebSocket functionality")
        _, _, _, instance_url = normalize_instance(instance=instance)
        self.auth_token = auth_token
        self.ws_url = f"{http_to_websocket_base(instance_url)}/ws?protocol=1&auth_token={auth_token}"
        self.command_timeout = command_timeout
        self.on_event = on_event
        self.on_resync = on_resync
        self.reconnect = reconnect
        self.ping_interval = ping_interval
        self.max_backoff = max_backoff

        #: Channels :meth:`resync` is run for after a reconnect (add with :meth:`watch`).
        self.watched: set[str] = set()
        self.session_id: str | None = None
        self.epoch: str | None = None

        self._tracker = EventTracker()
        self._socket: Any = None
        self._runner: asyncio.Task | None = None
        self._pinger: asyncio.Task | None = None
        self._ready = asyncio.Event()
        self._closing = False
        self._hello_seen = False
        self._counter = 0
        self._pending: dict[str, asyncio.Future[Ack]] = {}
        self._queue: asyncio.Queue[Any] = asyncio.Queue()
        self._resync_queue: set[str] = set()
        self._resync_task: asyncio.Task | None = None
        self._tasks: set[asyncio.Task] = set()
        self._failure: Exception | None = None

    # ── lifecycle ──────────────────────────────────────────────

    async def start(self, *, timeout: float = 15.0) -> "ProtocolClient":
        """Connect and wait for the server's ``hello``."""
        if self._runner is None:
            self._closing = False
            self._runner = asyncio.create_task(self._run(), name="pypufferblow-protocol")
        try:
            await asyncio.wait_for(self._ready.wait(), timeout)
        except asyncio.TimeoutError:
            await self.close()
            raise ProtocolError("NOT_CONNECTED", "Could not connect to the server in time.", retryable=True) from self._failure
        return self

    async def close(self) -> None:
        self._closing = True
        self._ready.clear()
        socket = self._socket
        if socket is not None:
            try:
                await socket.close()
            except Exception:  # noqa: BLE001
                pass
        for task in (self._runner, self._pinger, self._resync_task, *self._tasks):
            if task is not None and not task.done():
                task.cancel()
        self._runner = self._pinger = self._resync_task = None
        self._fail_pending("DISCONNECTED", "The client was closed.")
        self._queue.put_nowait(_CLOSED)

    async def __aenter__(self) -> "ProtocolClient":
        return await self.start()

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    @property
    def connected(self) -> bool:
        return self._ready.is_set()

    # ── events ─────────────────────────────────────────────────

    async def events(self) -> AsyncIterator[EventFrame]:
        """Iterate new events as they arrive; ends when the client is closed."""
        while True:
            item = await self._queue.get()
            if item is _CLOSED:
                self._queue.put_nowait(_CLOSED)  # let other iterators end too
                return
            yield item

    # ── commands ───────────────────────────────────────────────

    async def request(self, name: str, data: dict[str, Any], *, timeout: float | None = None) -> Ack:
        """Send a command and wait for its acknowledgment (the work is committed when it arrives)."""
        socket = self._socket
        if socket is None or not self._ready.is_set():
            raise ProtocolError("NOT_CONNECTED", "Not connected to the server.", retryable=True)

        self._counter += 1
        command_id = f"cmd_{self._counter}"
        future: asyncio.Future[Ack] = asyncio.get_running_loop().create_future()
        self._pending[command_id] = future
        try:
            try:
                await socket.send(build_command(command_id, name, data))
            except Exception as exc:  # noqa: BLE001
                raise ProtocolError("NOT_CONNECTED", "The connection closed while sending.", retryable=True) from exc
            try:
                return await asyncio.wait_for(future, timeout or self.command_timeout)
            except asyncio.TimeoutError:
                raise ProtocolError("TIMEOUT", "The server did not answer in time.", retryable=True) from None
        finally:
            self._pending.pop(command_id, None)

    async def send(self, name: str, data: dict[str, Any], *, timeout: float | None = None) -> dict[str, Any]:
        """Like :meth:`request`, returning just the result object."""
        return (await self.request(name, data, timeout=timeout)).result

    async def create_message(
        self,
        channel_id: str,
        content: str,
        *,
        nonce: str | None = None,
        retries: int = 2,
    ) -> ProtocolMessage:
        """Post a message.

        The ``nonce`` is the idempotency key. Retryable failures (a dropped connection, a timeout,
        a rate limit) are retried with the *same* nonce, so a message the server did commit is never
        posted twice. Pass your own nonce to retry across calls.
        """
        nonce = nonce or uuid.uuid4().hex
        attempt = 0
        while True:
            try:
                result = await self.send("message.create", {"channel_id": channel_id, "content": content, "nonce": nonce})
                break
            except ProtocolError as error:
                if not error.retryable or attempt >= retries:
                    raise
                attempt += 1
                await asyncio.sleep(error.retry_after if error.retry_after is not None else min(0.5 * 2**attempt, 5.0))
        message = ProtocolMessage.from_view(result.get("message"), channel_id)
        if message is None:
            raise ProtocolError("INTERNAL", "The server sent an unreadable message.")
        return message

    async def edit_message(self, channel_id: str, message_id: str, content: str) -> dict[str, Any]:
        return await self.send("message.edit", {"channel_id": channel_id, "message_id": message_id, "content": content})

    async def delete_message(self, channel_id: str, message_id: str) -> dict[str, Any]:
        return await self.send("message.delete", {"channel_id": channel_id, "message_id": message_id})

    async def add_reaction(self, channel_id: str, message_id: str, emoji: str) -> dict[str, Any]:
        return await self.send("reaction.add", {"channel_id": channel_id, "message_id": message_id, "emoji": emoji})

    async def remove_reaction(self, channel_id: str, message_id: str, emoji: str) -> dict[str, Any]:
        return await self.send("reaction.remove", {"channel_id": channel_id, "message_id": message_id, "emoji": emoji})

    async def subscribe(self, channel_id: str) -> None:
        """Start receiving a channel's events. The server already subscribes you to the channels you
        can see when you connect; this is for channels created afterwards."""
        result = await self.send("channel.subscribe", {"channel_id": channel_id})
        self._tracker.set_baseline(channel_id, _int(result.get("seq")), result.get("epoch"))

    async def unsubscribe(self, channel_id: str) -> None:
        await self.send("channel.unsubscribe", {"channel_id": channel_id})
        self._tracker.forget(channel_id)
        self.watched.discard(channel_id)

    def watch(self, *channel_ids: str) -> None:
        """Mark channels to catch up automatically after a reconnect or restart of the server."""
        self.watched.update(channel_ids)

    async def resync(self, channel_id: str, limit: int = DEFAULT_RESYNC_LIMIT) -> list[ProtocolMessage]:
        """The server's recent messages for a channel. Also moves the sequence baseline forward."""
        result = await self.send("events.resync", {"channel_id": channel_id, "limit": limit})
        self._tracker.set_baseline(channel_id, _int(result.get("seq")), result.get("epoch"))
        views = result.get("messages")
        return [m for m in (ProtocolMessage.from_view(v, channel_id) for v in (views if isinstance(views, list) else [])) if m]

    # ── internals ──────────────────────────────────────────────

    async def _run(self) -> None:
        attempt = 0
        while not self._closing:
            try:
                async with websockets.connect(self.ws_url) as socket:
                    self._socket = socket
                    attempt = 0
                    self._pinger = asyncio.create_task(self._ping_loop(socket))
                    async for raw in socket:
                        self._handle(parse_frame(raw))
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - connection errors of every kind end up here
                self._failure = exc
                logger.debug("protocol connection ended: %s", exc)
            finally:
                self._socket = None
                self._ready.clear()
                if self._pinger is not None:
                    self._pinger.cancel()
                self._tracker.reset_connection()
                self._resync_queue.clear()
                self._fail_pending("DISCONNECTED", "The connection dropped before the server answered.")
            if self._closing or not self.reconnect:
                break
            await asyncio.sleep(min(self.max_backoff, 0.5 * 2**attempt))
            attempt += 1
        self._queue.put_nowait(_CLOSED)

    async def _ping_loop(self, socket: Any) -> None:
        while True:
            await asyncio.sleep(self.ping_interval)
            try:
                await socket.send('{"type": "ping"}')
            except Exception:  # noqa: BLE001
                return

    def _fail_pending(self, code: str, message: str) -> None:
        for future in list(self._pending.values()):
            if not future.done():
                future.set_exception(ProtocolError(code, message, retryable=True))

    def _handle(self, frame: Any) -> None:
        if frame is None:
            return
        if isinstance(frame, Hello):
            epoch_changed = self._tracker.observe_epoch(frame.epoch)
            self.session_id, self.epoch = frame.session_id, frame.epoch
            reconnected = self._hello_seen or epoch_changed
            self._hello_seen = True
            self._ready.set()
            if reconnected:
                for channel_id in list(self.watched):
                    self._schedule_resync(channel_id)
        elif isinstance(frame, Ack):
            future = self._pending.get(frame.id)
            if future is not None and not future.done():
                future.set_result(frame)
        elif isinstance(frame, ErrorFrame):
            future = self._pending.get(frame.id) if frame.id else None
            if future is not None and not future.done():
                future.set_exception(frame.to_exception())
            else:
                logger.warning("server error %s: %s", frame.code, frame.message)
        elif isinstance(frame, EventFrame):
            apply, resync = self._tracker.accept(frame)
            if apply:
                if frame.name == "channel.updated" and (frame.data.get("deleted") or frame.data.get("access") == "revoked"):
                    if frame.channel_id:
                        self._tracker.forget(frame.channel_id)
                        self.watched.discard(frame.channel_id)
                self._queue.put_nowait(frame)
                self._call(self.on_event, frame)
            if resync and frame.channel_id:
                self._schedule_resync(frame.channel_id)

    def _call(self, callback: Callable[..., Any] | None, *args: Any) -> None:
        if callback is None:
            return
        try:
            outcome = callback(*args)
            if inspect.isawaitable(outcome):
                task = asyncio.ensure_future(self._guard(outcome))
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)
        except Exception:  # noqa: BLE001 - a bad handler must not kill the connection
            logger.exception("event handler failed")

    @staticmethod
    async def _guard(awaitable: Awaitable[Any]) -> None:
        try:
            await awaitable
        except Exception:  # noqa: BLE001
            logger.exception("event handler failed")

    # Resyncs run one at a time so a reconnect with many channels cannot trip the server's rate limit.
    def _schedule_resync(self, channel_id: str) -> None:
        self._resync_queue.add(channel_id)
        if self._resync_task is None or self._resync_task.done():
            self._resync_task = asyncio.create_task(self._drain_resyncs())

    async def _drain_resyncs(self) -> None:
        while self._resync_queue:
            channel_id = self._resync_queue.pop()
            try:
                messages = await self.resync(channel_id)
            except ProtocolError as error:
                if error.code in ("DISCONNECTED", "NOT_CONNECTED"):
                    return
                logger.warning("resync of %s failed: %s", channel_id, error.code)
                continue
            self._call(self.on_resync, channel_id, messages)


def _int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
