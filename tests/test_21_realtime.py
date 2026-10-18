"""ProtocolClient against a scripted local websocket server."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable

import pytest
import websockets

from pypufferblow.protocol import ProtocolError
from pypufferblow.realtime import ProtocolClient


def view(message_id: str, channel: str = "c1", text: str = "hi") -> dict:
    return {
        "id": message_id,
        "channel_id": channel,
        "author_id": "u1",
        "author_name": "ada",
        "author_avatar_url": None,
        "content": text,
        "attachments": [],
        "reactions": [],
        "created_at": "2030-01-01T10:00:00+00:00",
        "edit_count": 0,
        "last_edited_at": None,
    }


def hello(epoch: str = "ep_1") -> str:
    return json.dumps({"type": "hello", "version": 1, "supported": [1], "session_id": "s", "epoch": epoch})


def ack(command: dict, result: dict, duplicate: bool = False) -> str:
    data = {"status": "completed", "result": result}
    if duplicate:
        data["duplicate"] = True
    return json.dumps({"type": "ack", "version": 1, "id": command["id"], "data": data})


def error(command: dict, code: str, retryable: bool = False, retry_after: float | None = None) -> str:
    body = {"code": code, "message": f"{code} happened", "retryable": retryable}
    if retry_after is not None:
        body["retry_after"] = retry_after
    return json.dumps({"type": "error", "version": 1, "id": command["id"], "error": body})


_event_ids = iter(range(1, 10_000))


def created(message_id: str, seq: int, channel: str = "c1", event_id: str | None = None) -> str:
    return json.dumps(
        {
            "type": "event",
            "version": 1,
            "id": event_id or f"evt_{next(_event_ids)}",
            "name": "message.created",
            "channel_id": channel,
            "seq": seq,
            "epoch": "ep_1",
            "data": view(message_id, channel),
        }
    )


class Server:
    """Accepts connections, says hello, and hands every command to a script."""

    def __init__(self, script: Callable[["Server", object, dict], Awaitable[None]] | None = None) -> None:
        self.script = script
        self.connections: list = []
        self.commands: list[dict] = []
        self.paths: list[str] = []
        self.offered: list[str] = []
        self.hello_epoch = "ep_1"
        self._server = None
        self.port = 0

    async def handler(self, ws) -> None:
        self.connections.append(ws)
        self.paths.append(ws.request.path)
        self.offered.append(ws.request.headers.get("Sec-WebSocket-Protocol", ""))
        await ws.send(hello(self.hello_epoch))
        async for raw in ws:
            frame = json.loads(raw)
            if frame.get("type") != "command":
                continue
            self.commands.append(frame)
            if self.script:
                await self.script(self, ws, frame)

    async def __aenter__(self) -> "Server":
        self._server = await websockets.serve(self.handler, "127.0.0.1", 0, subprotocols=["pufferblow.v1"])
        self.port = self._server.sockets[0].getsockname()[1]
        return self

    async def __aexit__(self, *_exc) -> None:
        self._server.close()
        await self._server.wait_closed()

    def client(self, **kwargs) -> ProtocolClient:
        kwargs.setdefault("command_timeout", 2.0)
        return ProtocolClient("tok", f"127.0.0.1:{self.port}", **kwargs)


def run(coro) -> None:
    asyncio.run(asyncio.wait_for(coro, 20))


async def until(condition: Callable[[], bool], timeout: float = 3.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while not condition():
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError("condition not met in time")
        await asyncio.sleep(0.01)


def test_connects_with_the_protocol_flag_and_the_token_in_a_subprotocol_and_waits_for_hello():
    async def main():
        async with Server() as server:
            async with server.client() as client:
                assert client.connected and client.session_id == "s" and client.epoch == "ep_1"
                assert server.paths == ["/ws?protocol=1"]  # no token in the URL
                assert server.offered == ["pufferblow.v1, bearer.tok"]

    run(main())


def test_create_message_sends_a_command_with_a_nonce_and_returns_the_server_message():
    async def script(server, ws, command):
        await ws.send(ack(command, {"message": view("m1", text=command["data"]["content"])}))

    async def main():
        async with Server(script) as server:
            async with server.client() as client:
                message = await client.create_message("c1", "hello", nonce="n1")
        assert (message.id, message.content, message.channel_id) == ("m1", "hello", "c1")
        assert server.commands[0] == {"type": "command", "version": 1, "id": "cmd_1", "name": "message.create", "data": {"channel_id": "c1", "content": "hello", "nonce": "n1"}}

    run(main())


def test_a_nonce_is_generated_when_none_is_given():
    async def script(server, ws, command):
        await ws.send(ack(command, {"message": view("m1")}))

    async def main():
        async with Server(script) as server:
            async with server.client() as client:
                await client.create_message("c1", "hello")
        assert len(server.commands[0]["data"]["nonce"]) >= 16

    run(main())


def test_answers_are_matched_by_id_even_out_of_order():
    held: list[dict] = []

    async def script(server, ws, command):
        held.append(command)
        if len(held) == 2:
            for c in reversed(held):
                await ws.send(ack(c, {"echo": c["data"]["tag"]}))

    async def main():
        async with Server(script) as server:
            async with server.client() as client:
                first, second = await asyncio.gather(client.send("a", {"tag": 1}), client.send("b", {"tag": 2}))
        assert (first, second) == ({"echo": 1}, {"echo": 2})

    run(main())


def test_a_refused_command_raises_with_the_servers_code():
    async def script(server, ws, command):
        await ws.send(error(command, "PERMISSION_DENIED"))

    async def main():
        async with Server(script) as server:
            async with server.client() as client:
                with pytest.raises(ProtocolError) as caught:
                    await client.delete_message("c1", "m1")
        assert caught.value.code == "PERMISSION_DENIED" and caught.value.retryable is False

    run(main())


def test_a_command_that_is_never_answered_times_out():
    async def main():
        async with Server() as server:
            async with server.client(command_timeout=0.2) as client:
                with pytest.raises(ProtocolError) as caught:
                    await client.send("message.delete", {"channel_id": "c1", "message_id": "m"})
        assert caught.value.code == "TIMEOUT" and caught.value.retryable

    run(main())


def test_commands_fail_at_once_when_not_connected():
    async def main():
        client = ProtocolClient("tok", "127.0.0.1:1")
        with pytest.raises(ProtocolError) as caught:
            await client.send("message.create", {})
        assert caught.value.code == "NOT_CONNECTED" and caught.value.retryable

    run(main())


def test_create_message_retries_with_the_same_nonce():
    attempts: list[str] = []

    async def script(server, ws, command):
        attempts.append(command["data"]["nonce"])
        if len(attempts) == 1:
            await ws.send(error(command, "RATE_LIMITED", retryable=True, retry_after=0.01))
        else:
            await ws.send(ack(command, {"message": view("m1")}, duplicate=False))

    async def main():
        async with Server(script) as server:
            async with server.client() as client:
                message = await client.create_message("c1", "hello")
        assert message.id == "m1"
        assert len(attempts) == 2 and attempts[0] == attempts[1]

    run(main())


def test_create_message_does_not_retry_a_refusal():
    async def script(server, ws, command):
        await ws.send(error(command, "PERMISSION_DENIED"))

    async def main():
        async with Server(script) as server:
            async with server.client() as client:
                with pytest.raises(ProtocolError):
                    await client.create_message("c1", "hello")
        assert len(server.commands) == 1

    run(main())


def test_create_message_gives_up_after_the_retry_budget():
    async def script(server, ws, command):
        await ws.send(error(command, "RATE_LIMITED", retryable=True, retry_after=0.01))

    async def main():
        async with Server(script) as server:
            async with server.client() as client:
                with pytest.raises(ProtocolError) as caught:
                    await client.create_message("c1", "hello", retries=1)
        assert caught.value.code == "RATE_LIMITED" and len(server.commands) == 2

    run(main())


def test_events_are_delivered_once_to_callbacks_and_the_iterator():
    got: list[str] = []

    async def main():
        async with Server() as server:
            async with server.client(on_event=lambda e: got.append(e.id)) as client:
                ws = server.connections[0]
                repeated = created("m1", 1, event_id="evt_same")
                await ws.send(repeated)
                await ws.send(repeated)
                await ws.send(created("m2", 2))
                await until(lambda: len(got) == 2)
                stream = client.events()
                first = await asyncio.wait_for(stream.__anext__(), 1)
                second = await asyncio.wait_for(stream.__anext__(), 1)
        assert [first.data["id"], second.data["id"]] == ["m1", "m2"]

    run(main())


def test_async_callbacks_are_awaited_and_a_failing_callback_does_not_break_the_connection():
    got: list[str] = []

    async def on_event(event):
        got.append(event.data["id"])
        raise RuntimeError("handler bug")

    async def main():
        async with Server() as server:
            async with server.client(on_event=on_event) as client:
                ws = server.connections[0]
                await ws.send(created("m1", 1))
                await ws.send(created("m2", 2))
                await until(lambda: got == ["m1", "m2"])
                assert client.connected

    run(main())


def test_a_gap_triggers_a_resync_and_reports_the_servers_window():
    windows: list[tuple[str, list[str]]] = []

    async def script(server, ws, command):
        assert command["name"] == "events.resync"
        await ws.send(ack(command, {"channel_id": "c1", "messages": [view("m1"), view("m2"), view("m3"), view("m4")], "seq": 4, "epoch": "ep_1"}))

    async def main():
        async with Server(script) as server:
            async with server.client(on_resync=lambda ch, msgs: windows.append((ch, [m.id for m in msgs]))) as client:
                ws = server.connections[0]
                await ws.send(created("m1", 1))
                await ws.send(created("m4", 4))  # 2 and 3 were missed
                await until(lambda: windows)
                await ws.send(created("m5", 5))  # in order after the resync baseline
                await asyncio.sleep(0.1)
        assert windows == [("c1", ["m1", "m2", "m3", "m4"])]
        assert len(server.commands) == 1
        assert client.watched == set()

    run(main())


def test_a_reconnect_resyncs_watched_channels():
    windows: list[str] = []

    async def script(server, ws, command):
        await ws.send(ack(command, {"channel_id": command["data"]["channel_id"], "messages": [view("m1")], "seq": 1, "epoch": "ep_1"}))

    async def main():
        async with Server(script) as server:
            async with server.client(on_resync=lambda ch, msgs: windows.append(ch), max_backoff=0.05) as client:
                client.watch("c1")
                assert not server.commands  # nothing to catch up on at first connect
                await server.connections[0].close()
                await until(lambda: len(server.connections) == 2 and server.commands)
                await until(lambda: windows == ["c1"])
        assert server.commands[0]["name"] == "events.resync"

    run(main())


def test_commands_in_flight_fail_when_the_connection_drops():
    async def script(server, ws, command):
        await ws.close()

    async def main():
        async with Server(script) as server:
            async with server.client(reconnect=False) as client:
                with pytest.raises(ProtocolError) as caught:
                    await client.send("message.delete", {"channel_id": "c1", "message_id": "m"})
        assert caught.value.code in ("DISCONNECTED", "NOT_CONNECTED") and caught.value.retryable

    run(main())


def test_close_ends_the_event_stream_and_fails_pending_commands():
    async def main():
        async with Server() as server:
            client = await server.client().start()
            pending = asyncio.create_task(client.send("message.delete", {"channel_id": "c1", "message_id": "m"}))
            await asyncio.sleep(0.05)
            await client.close()
            with pytest.raises(ProtocolError) as caught:
                await pending
            assert caught.value.code == "DISCONNECTED"
            assert [event async for event in client.events()] == []
            assert not client.connected

    run(main())


def test_start_fails_cleanly_when_nothing_is_listening():
    async def main():
        client = ProtocolClient("tok", "127.0.0.1:1", reconnect=False)
        with pytest.raises(ProtocolError) as caught:
            await client.start(timeout=0.3)
        assert caught.value.code == "NOT_CONNECTED"

    run(main())


def test_subscribe_edit_react_helpers_send_the_right_commands():
    async def script(server, ws, command):
        result = {"channel_id": "c1", "seq": 3, "epoch": "ep_1", "subscribed": True, "reactions": []}
        await ws.send(ack(command, result))

    async def main():
        async with Server(script) as server:
            async with server.client() as client:
                await client.subscribe("c1")
                await client.edit_message("c1", "m1", "new")
                await client.add_reaction("c1", "m1", "👍")
                await client.remove_reaction("c1", "m1", "👍")
                await client.unsubscribe("c1")
        assert [(c["name"], c["data"]) for c in server.commands] == [
            ("channel.subscribe", {"channel_id": "c1"}),
            ("message.edit", {"channel_id": "c1", "message_id": "m1", "content": "new"}),
            ("reaction.add", {"channel_id": "c1", "message_id": "m1", "emoji": "👍"}),
            ("reaction.remove", {"channel_id": "c1", "message_id": "m1", "emoji": "👍"}),
            ("channel.unsubscribe", {"channel_id": "c1"}),
        ]

    run(main())
