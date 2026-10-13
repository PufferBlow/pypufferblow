"""Frame parsing, event de-duplication and the legacy adapter for protocol v1."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pypufferblow.bot import Bot, BotOptions
from pypufferblow.models.message_model import WebSocketMessage
from pypufferblow.protocol import (
    Ack,
    ErrorFrame,
    EventFrame,
    EventTracker,
    Hello,
    ProtocolError,
    ProtocolMessage,
    build_command,
    event_to_legacy,
    parse_frame,
)
from pypufferblow.websocket import GlobalWebSocket, create_global_websocket

FIXTURES = Path(__file__).parent / "fixtures" / "protocol_v1"
SERVER_FIXTURES = Path(__file__).resolve().parents[2] / "pufferblow" / "docs" / "protocol" / "v1" / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def all_fixtures() -> list[tuple[str, dict]]:
    return [(p.stem, json.loads(p.read_text(encoding="utf-8"))) for p in sorted(FIXTURES.glob("*.json"))]


def event(name: str) -> EventFrame:
    frame = parse_frame(load(name)["frame"])
    assert isinstance(frame, EventFrame)
    return frame


# ── the shared contract ──────────────────────────────────────────


def test_fixtures_are_present():
    assert len(all_fixtures()) >= 19


@pytest.mark.skipif(not SERVER_FIXTURES.exists(), reason="server checkout not next to this repo")
def test_fixtures_match_the_servers_copy():
    for path in SERVER_FIXTURES.glob("*.json"):
        assert (FIXTURES / path.name).read_bytes() == path.read_bytes(), f"{path.name} drifted from the server's copy"


@pytest.mark.parametrize("name,fixture", [f for f in all_fixtures() if f[1]["direction"] == "server_to_client"])
def test_every_server_fixture_parses(name, fixture):
    assert parse_frame(fixture["frame"]) is not None, name


@pytest.mark.parametrize("name,fixture", [f for f in all_fixtures() if f[1]["direction"] == "client_to_server"])
def test_every_client_fixture_is_what_we_build(name, fixture):
    frame = fixture["frame"]
    assert json.loads(build_command(frame["id"], frame["name"], frame["data"])) == frame, name


# ── parsing ──────────────────────────────────────────────────────


def test_hello():
    assert parse_frame(load("hello")["frame"]) == Hello(supported=(1,), session_id="ses_abc123", epoch="ep_1")


def test_ack_and_duplicate_flag():
    ack = parse_frame(load("ack_message_create")["frame"])
    assert isinstance(ack, Ack) and ack.id == "cmd_1" and not ack.duplicate
    assert ack.result["message"]["id"] == "m_8f2a"
    assert parse_frame(load("ack_message_create_duplicate")["frame"]).duplicate is True


def test_errors_with_and_without_a_command_id():
    limited = parse_frame(load("error_rate_limited")["frame"])
    assert limited == ErrorFrame(id="cmd_1", code="RATE_LIMITED", message="You are sending commands too quickly.", retryable=True, retry_after=0.4)
    error = limited.to_exception()
    assert isinstance(error, ProtocolError) and error.code == "RATE_LIMITED" and error.retryable and error.retry_after == 0.4
    assert parse_frame(load("error_malformed_no_id")["frame"]).id is None


def test_event_carries_channel_sequence_and_epoch():
    frame = event("event_message_created")
    assert (frame.name, frame.channel_id, frame.seq, frame.epoch) == ("message.created", "c_general", 41, "ep_1")
    presence = event("event_presence_changed")
    assert presence.channel_id is None and presence.seq is None


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        "[1, 2]",
        b"\x00\x01",
        None,
        json.dumps({"type": "event", "version": 2, "id": "e", "name": "x", "data": {}}),
        json.dumps({"type": "event", "version": 1, "name": "x", "data": {}}),
        json.dumps({"type": "ack", "version": 1, "id": "cmd_1"}),
        json.dumps({"type": "something_new", "version": 1}),
        json.dumps({"type": "pong"}),
    ],
)
def test_unknown_or_malformed_frames_are_ignored(raw):
    assert parse_frame(raw) is None


def test_message_from_view():
    message = ProtocolMessage.from_view(load("ack_message_create")["frame"]["data"]["result"]["message"])
    assert message == ProtocolMessage(
        id="m_8f2a",
        channel_id="c_general",
        author_id="u_ada",
        author_name="ada",
        content="Hello!",
        created_at="2030-01-01T10:00:00+00:00",
    )
    assert ProtocolMessage.from_view({"content": "no id"}) is None
    assert ProtocolMessage.from_view("nope") is None


# ── tracker ──────────────────────────────────────────────────────


def frame(seq=1, channel="c1", event_id=None, epoch="ep_1") -> EventFrame:
    frame.counter += 1
    return EventFrame(id=event_id or f"evt_{frame.counter}", name="message.created", data={}, channel_id=channel, seq=seq, epoch=epoch)


frame.counter = 0


def test_tracker_skips_repeats_and_notices_gaps():
    tracker = EventTracker()
    tracker.observe_epoch("ep_1")
    first = frame(10)
    assert tracker.accept(first) == (True, False)
    assert tracker.accept(first) == (False, False)
    assert tracker.accept(frame(11)) == (True, False)
    assert tracker.accept(frame(14)) == (True, True)  # 12 and 13 never arrived
    assert tracker.accept(frame(15)) == (True, False)


def test_tracker_follows_each_channel_separately():
    tracker = EventTracker()
    tracker.observe_epoch("ep_1")
    tracker.accept(frame(5, "a"))
    tracker.accept(frame(90, "b"))
    assert tracker.accept(frame(6, "a")) == (True, False)
    assert tracker.accept(frame(91, "b")) == (True, False)


def test_tracker_epoch_changes_mean_resync():
    tracker = EventTracker()
    assert tracker.observe_epoch("ep_1") is False
    tracker.accept(frame(10))
    assert tracker.accept(frame(1, epoch="ep_2")) == (True, True)
    assert tracker.observe_epoch("ep_3") is True


def test_tracker_baseline_from_a_resync_moves_the_position():
    tracker = EventTracker()
    tracker.observe_epoch("ep_1")
    tracker.accept(frame(10))
    tracker.set_baseline("c1", 20, "ep_1")
    assert tracker.accept(frame(21)) == (True, False)
    assert tracker.accept(frame(25)) == (True, True)


def test_tracker_passes_presence_and_forgets_channels():
    tracker = EventTracker()
    tracker.observe_epoch("ep_1")
    assert tracker.accept(EventFrame(id="p1", name="presence.changed", data={})) == (True, False)
    tracker.accept(frame(10))
    tracker.forget("c1")
    assert tracker.accept(frame(50)) == (True, False)


def test_tracker_remembers_only_recent_ids():
    tracker = EventTracker()
    old = EventFrame(id="old", name="presence.changed", data={})
    tracker.accept(old)
    for i in range(EventTracker.SEEN_LIMIT + 5):
        tracker.accept(EventFrame(id=f"x{i}", name="presence.changed", data={}))
    assert tracker.accept(old) == (True, False)


# ── legacy adapter ───────────────────────────────────────────────


def test_message_created_becomes_the_legacy_message_shape():
    legacy = event_to_legacy(event("event_message_created"))
    assert legacy["type"] == "message"
    assert (legacy["message_id"], legacy["channel_id"], legacy["sender_user_id"], legacy["username"], legacy["message"]) == (
        "m_8f2a",
        "c_general",
        "u_ada",
        "ada",
        "Hello!",
    )


def test_other_events_map_to_their_legacy_names():
    assert event_to_legacy(event("event_message_updated")) == {
        "type": "message_edited",
        "message_id": "m_8f2a",
        "channel_id": "c_general",
        "message": "Hello, world!",
        "edit_count": 1,
        "last_edited_at": "2030-01-01T10:05:00+00:00",
    }
    assert event_to_legacy(event("event_reaction_added"))["type"] == "message_reaction_added"
    assert event_to_legacy(event("event_presence_changed")) == {"type": "user_status_changed", "user_id": "u_ada", "status": "idle"}


def test_events_without_a_legacy_form_are_not_forwarded():
    assert event_to_legacy(event("event_message_deleted")) is None
    assert event_to_legacy(event("event_channel_updated")) is None


# ── GlobalWebSocket in protocol mode ─────────────────────────────


def test_global_websocket_opts_in_with_the_protocol_parameter():
    legacy = create_global_websocket("tok", instance="localhost:7575")
    modern = create_global_websocket("tok", instance="localhost:7575", protocol=True)
    assert legacy._get_ws_url() == "ws://localhost:7575/ws?auth_token=tok"
    assert modern._get_ws_url() == "ws://localhost:7575/ws?auth_token=tok&protocol=1"


def test_global_websocket_delivers_v1_events_as_web_socket_messages_once():
    socket = GlobalWebSocket("tok", "http://localhost:7575", protocol=True)
    received: list[WebSocketMessage] = []
    socket.on_message = received.append

    socket._handle_protocol_frame(json.dumps(load("hello")["frame"]))
    created = json.dumps(load("event_message_created")["frame"])
    socket._handle_protocol_frame(created)
    socket._handle_protocol_frame(created)  # a repeat of the same event id
    socket._handle_protocol_frame(json.dumps(load("event_message_deleted")["frame"]))  # no legacy form
    socket._handle_protocol_frame(json.dumps(load("ack_message_create")["frame"]))
    socket._handle_protocol_frame("garbage")

    assert len(received) == 1
    assert received[0].type == "message" and received[0].message == "Hello!" and received[0].username == "ada"


# ── Bot ──────────────────────────────────────────────────────────


class _Client:
    def __init__(self):
        self.calls = []

    def websocket(self, **kwargs):
        self.calls.append(kwargs)
        return object()


def test_bot_asks_for_a_protocol_websocket_only_when_told_to():
    plain, modern = _Client(), _Client()
    Bot(BotOptions(host="localhost", port=7575, username="b", password="p"), client=plain).get_global_websocket()
    Bot(BotOptions(host="localhost", port=7575, username="b", password="p", use_protocol=True), client=modern).get_global_websocket()
    assert plain.calls == [{}]
    assert modern.calls == [{"protocol": True}]
