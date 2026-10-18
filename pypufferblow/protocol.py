"""
Wire format of the Pufferblow command/event protocol, version 1.

The server's ``docs/protocol/v1/fixtures/*.json`` are the contract; ``tests/fixtures/protocol_v1``
holds an identical copy that the test suite parses. Unknown frames resolve to ``None`` so a
newer server can add frames without breaking an older SDK.
"""

__all__ = [
    "PROTOCOL_VERSION",
    "ProtocolError",
    "Hello",
    "Ack",
    "ErrorFrame",
    "EventFrame",
    "ProtocolMessage",
    "EventTracker",
    "parse_frame",
    "build_command",
    "event_to_legacy",
]

import json
import re
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Union
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

PROTOCOL_VERSION = 1


class ProtocolError(Exception):
    """A command the server refused, or that never got an answer.

    ``code`` is one of the server's codes (``PERMISSION_DENIED``, ``RATE_LIMITED``, ...) or one of
    three raised locally: ``NOT_CONNECTED``, ``DISCONNECTED`` and ``TIMEOUT``. ``retryable`` means
    sending the same command again is safe; for ``message.create`` the repeated ``nonce`` makes
    sure the server never posts the message twice.
    """

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.retryable = retryable
        self.retry_after = retry_after


@dataclass(frozen=True)
class Hello:
    supported: tuple[int, ...]
    session_id: str
    epoch: str


@dataclass(frozen=True)
class Ack:
    id: str
    result: dict[str, Any]
    #: True when the server recognised the command's nonce and returned the stored result.
    duplicate: bool = False


@dataclass(frozen=True)
class ErrorFrame:
    #: ``None`` when the server could not tell which command the frame was for.
    id: str | None
    code: str
    message: str
    retryable: bool = False
    retry_after: float | None = None

    def to_exception(self) -> ProtocolError:
        return ProtocolError(self.code, self.message, retryable=self.retryable, retry_after=self.retry_after)


WS_SUBPROTOCOL = "pufferblow.v1"
_SUBPROTOCOL_TOKEN = re.compile(r"^[A-Za-z0-9._~-]+$")


def split_credential(url: str) -> tuple[str, list[str]]:
    """Move ``auth_token`` out of a websocket URL into the subprotocols the server reads it from.

    Keeps the token out of access logs. A token a subprotocol cannot carry stays in the URL.
    """
    parts = urlsplit(url)
    pairs = parse_qsl(parts.query, keep_blank_values=True)
    token = next((v for k, v in pairs if k == "auth_token"), None)
    if not token or not _SUBPROTOCOL_TOKEN.match(token):
        return url, []
    query = urlencode([(k, v) for k, v in pairs if k != "auth_token"])
    return urlunsplit(parts._replace(query=query)), [WS_SUBPROTOCOL, f"bearer.{token}"]


@dataclass(frozen=True)
class EventFrame:
    id: str
    name: str
    data: dict[str, Any]
    channel_id: str | None = None
    seq: int | None = None
    epoch: str | None = None


Frame = Union[Hello, Ack, ErrorFrame, EventFrame]


@dataclass(frozen=True)
class ProtocolMessage:
    """A message as the v1 protocol describes it (``message.created``, acks, resync)."""

    id: str
    channel_id: str
    author_id: str
    author_name: str
    content: str
    created_at: str
    author_avatar_url: str | None = None
    attachments: list[Any] = field(default_factory=list)
    reactions: list[dict[str, Any]] = field(default_factory=list)
    edit_count: int = 0
    last_edited_at: str | None = None

    @classmethod
    def from_view(cls, view: Any, fallback_channel_id: str = "") -> "ProtocolMessage | None":
        """Build from a v1 message object; ``None`` when it has no id or timestamp."""
        if not isinstance(view, dict):
            return None
        message_id, created_at = view.get("id"), view.get("created_at")
        if not isinstance(message_id, str) or not isinstance(created_at, str):
            return None
        return cls(
            id=message_id,
            channel_id=view.get("channel_id") or fallback_channel_id,
            author_id=view.get("author_id") or "",
            author_name=view.get("author_name") or "Unknown user",
            content=view.get("content") or "",
            created_at=created_at,
            author_avatar_url=view.get("author_avatar_url"),
            attachments=list(view.get("attachments") or []),
            reactions=list(view.get("reactions") or []),
            edit_count=int(view.get("edit_count") or 0),
            last_edited_at=view.get("last_edited_at"),
        )


def _number(value: Any) -> float | int | None:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def parse_frame(raw: Any) -> Frame | None:
    """Decode one inbound text frame. Anything that is not a well-formed v1 frame is ``None``."""
    if isinstance(raw, (bytes, bytearray)):
        return None
    frame = raw
    if isinstance(raw, str):
        try:
            frame = json.loads(raw)
        except ValueError:
            return None
    if not isinstance(frame, dict) or frame.get("version") != PROTOCOL_VERSION:
        return None

    kind = frame.get("type")
    if kind == "hello":
        session_id, epoch = frame.get("session_id"), frame.get("epoch")
        if not isinstance(session_id, str) or not isinstance(epoch, str):
            return None
        supported = tuple(n for n in frame.get("supported") or [] if isinstance(n, int))
        return Hello(supported=supported, session_id=session_id, epoch=epoch)

    if kind == "ack":
        data = frame.get("data")
        if not isinstance(frame.get("id"), str) or not isinstance(data, dict):
            return None
        result = data.get("result")
        return Ack(id=frame["id"], result=result if isinstance(result, dict) else {}, duplicate=data.get("duplicate") is True)

    if kind == "error":
        error = frame.get("error")
        if not isinstance(error, dict):
            return None
        command_id = frame.get("id")
        return ErrorFrame(
            id=command_id if isinstance(command_id, str) else None,
            code=str(error.get("code") or "INTERNAL"),
            message=str(error.get("message") or "Unknown error"),
            retryable=error.get("retryable") is True,
            retry_after=_number(error.get("retry_after")),
        )

    if kind == "event":
        data = frame.get("data")
        if not isinstance(frame.get("id"), str) or not isinstance(frame.get("name"), str) or not isinstance(data, dict):
            return None
        channel_id, epoch = frame.get("channel_id"), frame.get("epoch")
        seq = _number(frame.get("seq"))
        return EventFrame(
            id=frame["id"],
            name=frame["name"],
            data=data,
            channel_id=channel_id if isinstance(channel_id, str) else None,
            seq=int(seq) if seq is not None else None,
            epoch=epoch if isinstance(epoch, str) else None,
        )

    return None


def build_command(command_id: str, name: str, data: dict[str, Any]) -> str:
    """Serialise a command frame, ready to send."""
    return json.dumps({"type": "command", "version": PROTOCOL_VERSION, "id": command_id, "name": name, "data": data})


class EventTracker:
    """Skips duplicate events (by event id) and notices gaps.

    Delivery is at-least-once and in order per channel within one server epoch. Sequence numbers
    are per channel; the epoch changes when the server restarts, so a new epoch means anything
    may have been missed.
    """

    SEEN_LIMIT = 1000

    def __init__(self) -> None:
        self._seen: OrderedDict[str, None] = OrderedDict()
        self._seqs: dict[str, int] = {}
        self._epoch: str | None = None

    def observe_epoch(self, epoch: str) -> bool:
        """Record the epoch from a ``hello``; True when it differs from the previous one."""
        changed = self._epoch is not None and self._epoch != epoch
        if changed:
            self._seqs.clear()
        self._epoch = epoch
        return changed

    def set_baseline(self, channel_id: str, seq: int | None, epoch: str | None = None) -> None:
        """Take the position a subscribe or resync ack reports for a channel."""
        if epoch is not None and self._epoch is not None and epoch != self._epoch:
            self._seqs.clear()
            self._epoch = epoch
        if seq is not None:
            self._seqs[channel_id] = seq

    def forget(self, channel_id: str) -> None:
        self._seqs.pop(channel_id, None)

    def reset_connection(self) -> None:
        self._seqs.clear()

    def accept(self, frame: EventFrame) -> tuple[bool, bool]:
        """Return ``(apply, resync)``: whether to handle the event and whether a channel needs a resync."""
        if frame.id in self._seen:
            return False, False
        self._seen[frame.id] = None
        if len(self._seen) > self.SEEN_LIMIT:
            self._seen.popitem(last=False)

        if frame.channel_id is None or frame.seq is None:
            return True, False

        if frame.epoch is not None and self._epoch is not None and frame.epoch != self._epoch:
            self._epoch = frame.epoch
            self._seqs.clear()
            self._seqs[frame.channel_id] = frame.seq
            return True, True

        last = self._seqs.get(frame.channel_id)
        if last is None:
            self._seqs[frame.channel_id] = frame.seq
            return True, False
        if frame.seq <= last:
            return True, False  # late or repeated; handlers are idempotent
        self._seqs[frame.channel_id] = frame.seq
        return True, frame.seq > last + 1


def event_to_legacy(frame: EventFrame) -> dict[str, Any] | None:
    """Translate a v1 event to the dict shape the pre-protocol websocket pushed.

    This lets code written for ``WebSocketMessage`` (including :class:`pypufferblow.bot.Bot`) keep
    working over protocol v1. Events with no legacy equivalent return ``None``.
    """
    data = frame.data
    if frame.name == "message.created":
        message = ProtocolMessage.from_view(data, frame.channel_id or "")
        if message is None:
            return None
        return {
            "type": "message",
            "message_id": message.id,
            "channel_id": message.channel_id,
            "sender_user_id": message.author_id,
            "username": message.author_name,
            "sender_avatar_url": message.author_avatar_url,
            "message": message.content,
            "sent_at": message.created_at,
            "attachments": message.attachments,
        }
    if frame.name == "message.updated":
        return {
            "type": "message_edited",
            "message_id": data.get("id"),
            "channel_id": data.get("channel_id") or frame.channel_id,
            "message": data.get("content"),
            "edit_count": data.get("edit_count"),
            "last_edited_at": data.get("last_edited_at"),
        }
    if frame.name in ("reaction.added", "reaction.removed"):
        suffix = "added" if frame.name.endswith("added") else "removed"
        return {"type": f"message_reaction_{suffix}", **{k: data.get(k) for k in ("message_id", "channel_id", "user_id", "emoji", "reactions")}}
    if frame.name == "presence.changed":
        return {"type": "user_status_changed", "user_id": data.get("user_id"), "status": data.get("status")}
    return None
