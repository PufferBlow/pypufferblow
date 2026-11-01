"""Deleting your own account."""

from __future__ import annotations

import pytest
import requests

from pypufferblow.exceptions import BadAuthToken, InvalidPassword, ServerError
from pypufferblow.models.route_model import Route
from pypufferblow.routes import users_routes
from pypufferblow.users import Users, UsersOptions


class Reply:
    def __init__(self, status: int, payload: dict | None = None) -> None:
        self.status_code = status
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload


def signed_in() -> Users:
    users = Users(UsersOptions(instance="http://home.example:7575", username="ada", password="12345678"))
    users.SIGNIN_API_ROUTE = Route("http://home.example:7575/api/v1/users/signin", methods=["GET"])
    users.user = type("U", (), {"auth_token": "tok"})()
    users.is_signed_in = True
    return users


def answer(monkeypatch, reply: Reply):
    seen = {}

    def post(url, **kwargs):
        seen["url"], seen["json"] = url, kwargs["json"]
        return reply

    monkeypatch.setattr(requests, "post", post)
    return seen


def test_deleting_sends_the_password_again_and_ends_the_session(monkeypatch):
    seen = answer(monkeypatch, Reply(200, {"deleted": True}))
    users = signed_in()
    users.delete_account()
    assert seen == {"url": "http://home.example:7575/api/v1/users/delete", "json": {"auth_token": "tok", "password": "12345678"}}
    assert users.is_signed_in is False


@pytest.mark.parametrize(
    "reply, error",
    [
        (Reply(401, {"error_code": "auth.invalid_credentials"}), InvalidPassword),
        (Reply(401, {"error_code": "auth.invalid_token"}), BadAuthToken),
        (Reply(409, {"error_code": "account.owner_cannot_delete"}), ServerError),
    ],
)
def test_a_refusal_raises_what_it_was(monkeypatch, reply, error):
    answer(monkeypatch, reply)
    users = signed_in()
    with pytest.raises(error):
        users.delete_account()
    assert users.is_signed_in is True


def test_the_route_table_is_unchanged():
    assert len(users_routes) == 8
