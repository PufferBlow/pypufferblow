from __future__ import annotations

import pytest

import pypufferblow.calls as calls_module
from pypufferblow.calls import Calls, CallsOptions
from pypufferblow.exceptions import BadAuthToken, CallBusy, CallRefused, UserNotFound
from pypufferblow.models.route_model import Route
from pypufferblow.routes import calls_routes


class Reply:
    def __init__(self, status: int = 200, body: dict | None = None) -> None:
        self.status_code, self._body = status, body or {}

    def json(self) -> dict:
        return self._body


@pytest.fixture
def sdk(monkeypatch):
    calls: list[dict] = []
    state = {"reply": Reply()}

    def fake(method):
        def call(url, **kwargs):
            calls.append({"method": method, "url": url, **kwargs})
            return state["reply"]

        return call

    for method in ("get", "post", "put", "delete"):
        monkeypatch.setattr(calls_module.requests, method, fake(method.upper()))
    client = Calls(CallsOptions(auth_token="secret-token", instance="https://chat.example.org"))
    names = ["INVITE", "ACCEPT", "REJECT", "END", "SIGNAL", "FALLBACK", "IDENTITY_KEYS", "IDENTITY_KEY"]
    for name, route in zip(names, calls_routes):
        setattr(client, f"{name}_API_ROUTE", Route("https://chat.example.org" + route.api_route, route.methods))
    return client, calls, state


def test_inviting_posts_the_callee_in_the_path_and_the_body(sdk):
    client, calls, state = sdk
    state["reply"] = Reply(200, {"call_id": "c1", "status": "ringing", "ice_servers": []})

    assert client.invite("u2")["call_id"] == "c1"

    sent = calls[0]
    assert sent["method"] == "POST" and sent["url"].endswith("/api/v1/dm-calls/u2/invite")
    assert sent["json"] == {"auth_token": "secret-token", "callee_id": "u2"}


def test_accept_reject_end_and_signal_hit_the_call(sdk):
    client, calls, state = sdk
    state["reply"] = Reply(200, {"status": "accepted"})
    client.accept("c1")
    client.reject("c1")
    client.end("c1")
    client.signal("c1", "relay", {"relay_key": {"v": 1}})
    client.join_relay("c1", "high")

    assert [c["url"].split("/api/v1/dm-calls")[1] for c in calls] == ["/c1/accept", "/c1/reject", "/c1/end", "/c1/signal", "/c1/fallback"]
    assert calls[3]["json"] == {"auth_token": "secret-token", "signal_type": "relay", "payload": {"relay_key": {"v": 1}}}
    assert calls[4]["json"]["quality_profile"] == "high"


def test_identity_keys_register_list_and_remove(sdk):
    client, calls, state = sdk
    jwk = {"kty": "EC", "crv": "P-256", "x": "x", "y": "y"}
    state["reply"] = Reply(200, {"created": True, "key": {"key_id": "k1"}})
    assert client.register_identity_key(jwk, "Laptop")["created"] is True
    assert calls[0]["method"] == "PUT" and calls[0]["json"] == {"auth_token": "secret-token", "public_key": jwk, "label": "Laptop"}

    state["reply"] = Reply(200, {"keys": [{"key_id": "k1"}]})
    assert client.list_identity_keys("u1") == [{"key_id": "k1"}]
    assert calls[1]["url"].endswith("/api/v1/identity-keys/u1") and calls[1]["params"] == {"auth_token": "secret-token"}

    client.remove_identity_key("k1")
    assert calls[2]["method"] == "DELETE" and calls[2]["url"].endswith("/api/v1/identity-keys/k1")


@pytest.mark.parametrize(
    ("status", "error"),
    [(401, BadAuthToken), (403, BadAuthToken), (404, UserNotFound), (409, CallBusy), (400, CallRefused)],
)
def test_refusals_become_the_error_that_says_what_was_wrong(sdk, status, error):
    client, _, state = sdk
    state["reply"] = Reply(status, {"detail": "Cannot call this user"})
    with pytest.raises(error) as caught:
        client.invite("u2")
    assert "secret-token" not in str(caught.value)
    if status == 400:
        assert caught.value.status_code == 400 and "Cannot call this user" in str(caught.value)


def test_a_busy_caller_error_is_a_call_refusal_too(sdk):
    client, _, state = sdk
    state["reply"] = Reply(409, {"detail": "You are already on a call"})
    with pytest.raises(CallRefused) as caught:  # callers can catch the family, or CallBusy for this case
        client.invite("u2")
    assert isinstance(caught.value, CallBusy) and caught.value.status_code == 409
