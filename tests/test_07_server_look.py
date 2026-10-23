"""The SDK's side of the server look and the welcome message: what is sent, and how refusals are named."""

from __future__ import annotations

import pytest

import pypufferblow.system as system_module
from pypufferblow.exceptions import NotAnAdminOrServerOwner, ServerError
from pypufferblow.system import System, SystemOptions


class Reply:
    def __init__(self, status: int = 200, body: dict | None = None) -> None:
        self.status_code, self._body = status, body or {}

    def json(self) -> dict:
        return self._body


@pytest.fixture
def sdk(monkeypatch):
    calls: list[dict] = []
    state = {"reply": Reply()}

    def put(url, **kwargs):
        calls.append({"url": url, **kwargs})
        return state["reply"]

    monkeypatch.setattr(system_module.requests, "put", put)
    client = System(SystemOptions(auth_token="tok", host="localhost", port=7575))
    return client, calls, state


def test_the_look_is_sent_as_one_object_and_the_whole_look_comes_back(sdk):
    client, calls, state = sdk
    state["reply"] = Reply(200, {"look": {"icon_style": "school", "tone": "sky", "tone2": None, "banner_pattern": None}})

    look = client.update_server_look(icon_style="school", tone="sky")

    assert calls[0]["url"].endswith("/api/v1/system/server-appearance")
    assert calls[0]["json"] == {"auth_token": "tok", "look": {"icon_style": "school", "tone": "sky"}}
    assert look["icon_style"] == "school"


def test_none_goes_back_to_the_derived_default(sdk):
    client, calls, _ = sdk
    client.update_server_look(tone=None)
    assert calls[0]["json"]["look"] == {"tone": None}


def test_a_name_that_is_not_a_look_setting_is_refused_before_anything_is_sent(sdk):
    client, calls, _ = sdk
    with pytest.raises(ValueError):
        client.update_server_look(colour="red")
    with pytest.raises(ValueError):
        client.update_server_look()
    assert calls == []


def test_a_refusal_is_named(sdk):
    client, _, state = sdk
    state["reply"] = Reply(403)
    with pytest.raises(NotAnAdminOrServerOwner):
        client.update_server_look(tone="sky")
    state["reply"] = Reply(400, {"message": "tone must be one of ['brass']"})
    with pytest.raises(ServerError, match="tone must be one of"):
        client.update_server_look(tone="neon")


def test_the_welcome_message_and_file_types_can_be_updated(sdk):
    client, calls, _ = sdk
    client.update_server_info(welcome_message="Hello", allowed_image_types=["png"])
    assert calls[0]["json"] == {"auth_token": "tok", "welcome_message": "Hello", "allowed_image_types": ["png"]}
