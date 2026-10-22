from __future__ import annotations

import pytest

import pypufferblow.federation as federation_module
from pypufferblow.exceptions import (
    BadAuthToken,
    InvalidPeerValue,
    NotAnAdminOrServerOwner,
    PeerAlreadyExists,
    PeerNotFound,
)
from pypufferblow.federation import Federation, FederationOptions
from pypufferblow.models.route_model import Route
from pypufferblow.routes import federation_routes


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
        monkeypatch.setattr(federation_module.requests, method, fake(method.upper()))
    client = Federation(FederationOptions(auth_token="secret-token", instance="https://chat.example.org"))
    base = "https://chat.example.org"
    for name, index in [
        ("PEERS_API_ROUTE", 1),
        ("MODE_API_ROUTE", 2),
        ("PEER_API_ROUTE", 3),
        ("PEER_STATUS_API_ROUTE", 4),
        ("PEER_POLICY_API_ROUTE", 5),
        ("PEER_REFRESH_API_ROUTE", 6),
        ("PEERS_IMPORT_API_ROUTE", 7),
    ]:
        route = federation_routes[index]
        setattr(client, name, Route(base + route.api_route, route.methods))
    return client, calls, state


def test_list_peers_returns_mode_counts_and_peers(sdk):
    client, calls, state = sdk
    state["reply"] = Reply(200, {"mode": "open", "modes": ["open"], "counts": {"blocked": 1}, "peers": [{"host": "a.example"}], "status_code": 200})
    result = client.list_peers()
    assert result["peers"] == [{"host": "a.example"}] and result["mode"] == "open"
    assert calls[0]["url"].endswith("/api/v1/federation/peers") and calls[0]["params"] == {"auth_token": "secret-token"}


def test_peer_changes_hit_the_right_routes(sdk):
    client, calls, state = sdk
    state["reply"] = Reply(200, {"peer": {"host": "a.example", "status": "blocked"}, "mode": "closed"})

    assert client.set_federation_mode("closed") == "closed"
    assert client.block_peer("a.example")["status"] == "blocked"
    client.accept_peer("a.example")
    client.set_peer_policy("a.example", media=False, voice=True)
    client.add_peer("b.example", "limited")

    methods = [(c["method"], c["url"].split("/api/v1/federation")[1]) for c in calls]
    assert methods == [
        ("PUT", "/mode"),
        ("PUT", "/peers/a.example/status"),
        ("PUT", "/peers/a.example/status"),
        ("PUT", "/peers/a.example/policy"),
        ("POST", "/peers"),
    ]
    assert calls[3]["json"] == {"auth_token": "secret-token", "policy": {"media": False, "voice": True}}
    assert calls[4]["json"]["status"] == "limited"


def test_remove_refresh_and_import(sdk):
    client, calls, state = sdk
    client.remove_peer("a.example")
    assert calls[0]["method"] == "DELETE" and calls[0]["params"] == {"auth_token": "secret-token"}

    state["reply"] = Reply(200, {"found": False, "peer": {"host": "a.example"}})
    assert client.refresh_peer("a.example") is None
    state["reply"] = Reply(200, {"found": True, "peer": {"host": "a.example", "software": "pufferblow"}})
    assert client.refresh_peer("a.example")["software"] == "pufferblow"

    state["reply"] = Reply(200, {"added": ["x.example"], "skipped": [], "invalid": ["bad host"]})
    assert client.import_peers(["x.example", "bad host"]) == {"added": ["x.example"], "skipped": [], "invalid": ["bad host"]}
    assert calls[-1]["json"]["status"] == "blocked"


@pytest.mark.parametrize(
    ("status", "error"),
    [(403, NotAnAdminOrServerOwner), (404, PeerNotFound), (409, PeerAlreadyExists), (401, BadAuthToken), (400, InvalidPeerValue)],
)
def test_refusals_become_the_error_that_says_what_was_wrong(sdk, status, error):
    client, _, state = sdk
    state["reply"] = Reply(status, {"details": {"field": "status"}})
    with pytest.raises(error) as caught:
        client.set_peer_status("a.example", "blocked")
    assert "secret-token" not in str(caught.value)
    if error is InvalidPeerValue:
        assert caught.value.field == "status"
