from __future__ import annotations

import logging

from pypufferblow.federation import Federation, FederationOptions


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self) -> dict:
        return self._payload


def test_federation_verbose_logging_emits_readable_follow_and_dm_messages(monkeypatch, caplog) -> None:
    federation = Federation(
        FederationOptions(
            instance="https://chat.example.org",
            auth_token="token-123",
            verbose=True,
        )
    )
    follow_url = federation.FOLLOW_REMOTE_API_ROUTE.api_route
    send_dm_url = federation.SEND_DIRECT_MESSAGE_API_ROUTE.api_route
    load_dm_url = federation.LOAD_DIRECT_MESSAGES_API_ROUTE.api_route

    def fake_post(url, json=None, **kwargs):
        if url == follow_url:
            return FakeResponse(200, {"ok": True})
        if url == send_dm_url:
            return FakeResponse(200, {"ok": True})
        raise AssertionError(f"Unhandled POST request: {url}")

    def fake_get(url, params=None, **kwargs):
        if url == load_dm_url:
            return FakeResponse(200, {"messages": [{"message_id": "dm-1"}]})
        raise AssertionError(f"Unhandled GET request: {url}")

    import pypufferblow.federation as federation_module

    monkeypatch.setattr(federation_module.requests, "post", fake_post)
    monkeypatch.setattr(federation_module.requests, "get", fake_get)
    caplog.set_level(logging.DEBUG, logger="pypufferblow")

    federation.follow_remote_account("alice@example.net")
    federation.send_direct_message("alice@example.net", "hello there")
    federation.load_direct_messages("alice@example.net")

    log_messages = [record.getMessage() for record in caplog.records if record.name.startswith("pypufferblow")]
    assert any("Following remote account handle=alice@example.net via home instance=https://chat.example.org" in message for message in log_messages)
    assert any("Sending direct message peer=alice@example.net via home instance=https://chat.example.org attachments=0" in message for message in log_messages)
    assert any("Loaded 1 direct messages for peer=alice@example.net" in message for message in log_messages)
