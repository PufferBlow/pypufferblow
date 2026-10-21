from __future__ import annotations

import pytest

import pypufferblow.channels as channels_module
from pypufferblow.channels import Channels, ChannelsOptions
from pypufferblow.exceptions import (
    BadAuthToken,
    CategoryNameAlreadyExists,
    CategoryNotFound,
    ChannelNotFound,
    MessageNotFound,
    NotAnAdminOrServerOwner,
    PinLimitReached,
)
from pypufferblow.models.channel_model import ChannelModel
from pypufferblow.models.user_model import UserModel


class Reply:
    def __init__(self, status: int = 200, body: dict | None = None) -> None:
        self.status_code, self._body = status, body or {}

    def json(self) -> dict:
        return self._body


@pytest.fixture
def sdk(monkeypatch):
    """A Channels client whose requests are recorded and answered by `answer`."""
    calls: list[dict] = []
    state = {"reply": Reply()}

    def fake(method):
        def call(url, **kwargs):
            calls.append({"method": method, "url": url, **kwargs})
            return state["reply"]

        return call

    for method in ("get", "post", "put", "delete"):
        monkeypatch.setattr(channels_module.requests, method, fake(method.upper()))
    user = UserModel(auth_token="secret-token", username="ada")
    client = Channels(ChannelsOptions(user=user, instance="https://chat.example.org", username="ada", password="x"))
    return client, calls, state


def test_a_channel_knows_its_category_position_and_topic():
    channel = ChannelModel().parse_json({"channel_id": "c1", "category_id": "cat1", "position": 2, "topic": "Patch talk"})
    assert (channel.category_id, channel.position, channel.topic) == ("cat1", 2, "Patch talk")
    assert ChannelModel().category_id is None and ChannelModel().topic is None and ChannelModel().position == 0


def test_update_channel_sends_only_the_fields_given(sdk):
    client, calls, state = sdk
    state["reply"] = Reply(200, {"channel_data": {"channel_id": "c1", "topic": "Patch talk"}})

    result = client.update_channel("c1", topic="Patch talk", category_id=None)

    assert result["topic"] == "Patch talk"
    sent = calls[0]
    assert sent["method"] == "PUT" and sent["url"].endswith("/api/v1/channels/c1/update")
    assert sent["json"] == {"auth_token": "secret-token", "topic": "Patch talk", "category_id": None}  # an explicit null is sent


def test_update_channel_refuses_a_field_that_is_not_one(sdk):
    client, calls, _ = sdk
    with pytest.raises(TypeError):
        client.update_channel("c1", channel_type="voice")
    assert calls == []


def test_an_unknown_category_on_update_is_a_category_error(sdk):
    client, _, state = sdk
    state["reply"] = Reply(404)
    with pytest.raises(CategoryNotFound):
        client.update_channel("c1", category_id="nope")
    with pytest.raises(ChannelNotFound):
        client.update_channel("c1", topic="x")


def test_categories_are_listed_created_renamed_reordered_and_deleted(sdk):
    client, calls, state = sdk

    state["reply"] = Reply(200, {"categories": [{"category_id": "a", "name": "A", "position": 0}]})
    assert client.list_categories()[0]["name"] == "A"
    assert calls[-1]["method"] == "GET" and calls[-1]["params"] == {"auth_token": "secret-token"}

    state["reply"] = Reply(201, {"category": {"category_id": "b", "name": "B", "position": 1}})
    assert client.create_category("B")["category_id"] == "b"
    assert calls[-1]["json"] == {"auth_token": "secret-token", "name": "B"}

    state["reply"] = Reply(200, {"category": {"category_id": "b", "name": "Beta", "position": 1}})
    assert client.rename_category("b", "Beta")["name"] == "Beta"
    assert calls[-1]["url"].endswith("/categories/b")

    state["reply"] = Reply(200, {"categories": []})
    client.reorder_categories(["b", "a"])
    assert calls[-1]["url"].endswith("/categories/order") and calls[-1]["json"]["category_ids"] == ["b", "a"]

    state["reply"] = Reply(200)
    client.delete_category("b")
    assert calls[-1]["method"] == "DELETE" and calls[-1]["url"].endswith("/categories/b")


def test_category_refusals_are_named(sdk):
    client, _, state = sdk
    state["reply"] = Reply(409)
    with pytest.raises(CategoryNameAlreadyExists):
        client.create_category("B")
    state["reply"] = Reply(404)
    with pytest.raises(CategoryNotFound):
        client.rename_category("zzz", "X")
    state["reply"] = Reply(403)
    with pytest.raises(NotAnAdminOrServerOwner):
        client.delete_category("a")


def test_pins_are_listed_pinned_and_unpinned(sdk):
    client, calls, state = sdk

    state["reply"] = Reply(200, {"pins": [{"message_id": "m1", "pinned_by": "u1"}], "limit": 50})
    assert client.list_pins("c1")[0]["message_id"] == "m1"
    assert calls[-1]["url"].endswith("/channels/c1/pins")

    state["reply"] = Reply(200, {"pinned": True, "already": False})
    assert client.pin_message("c1", "m1") is True
    assert calls[-1]["method"] == "PUT" and calls[-1]["url"].endswith("/channels/c1/messages/m1/pin")
    state["reply"] = Reply(200, {"pinned": True, "already": True})
    assert client.pin_message("c1", "m1") is False

    state["reply"] = Reply(200, {"pinned": False, "removed": True})
    assert client.unpin_message("c1", "m1") is True
    state["reply"] = Reply(200, {"pinned": False, "removed": False})
    assert client.unpin_message("c1", "m1") is False


def test_pin_refusals_are_named_and_never_quote_the_token(sdk):
    client, _, state = sdk
    state["reply"] = Reply(409)
    with pytest.raises(PinLimitReached):
        client.pin_message("c1", "m1")
    state["reply"] = Reply(404)
    with pytest.raises(MessageNotFound):
        client.pin_message("c1", "m1")
    state["reply"] = Reply(401)
    with pytest.raises(BadAuthToken) as caught:
        client.list_pins("c1")
    assert "secret-token" not in str(caught.value)
