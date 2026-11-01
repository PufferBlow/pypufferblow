"""Invitation codes, requests to join, and joining another server with your own account."""

from __future__ import annotations

import pytest
import requests

from pypufferblow.access import Access, AccessOptions
from pypufferblow.exceptions import InviteInvalid, JoinDenied, JoinPending, JoinRefused, NotAnAdminOrServerOwner
from pypufferblow.routes import access_routes


class Reply:
    def __init__(self, status: int, payload: dict | None = None) -> None:
        self.status_code = status
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload


def make() -> Access:
    access = Access(AccessOptions(instance="http://home.example:7575", auth_token="tok"))
    built = [route.__class__(f"http://home.example:7575{route.api_route}", methods=list(route.methods)) for route in access_routes]
    (
        access.INVITES_API_ROUTE,
        access.INVITE_API_ROUTE,
        access.JOIN_REQUESTS_API_ROUTE,
        access.APPROVE_REQUEST_API_ROUTE,
        access.DENY_REQUEST_API_ROUTE,
        access.ASSERTIONS_API_ROUTE,
        access.JOIN_API_ROUTE,
        access.JOIN_STATUS_API_ROUTE,
        access.LEAVE_API_ROUTE,
        access.KICK_API_ROUTE,
        access.REINSTATE_API_ROUTE,
    ) = built
    return access


@pytest.fixture
def calls(monkeypatch):
    log: list[tuple[str, str, dict]] = []
    answers: dict[tuple[str, str], Reply] = {}

    def fake(method):
        def call(url, **kwargs):
            log.append((method, url, kwargs))
            return answers.get((method, url.split("?")[0]), Reply(200, {}))

        return call

    for method in ("get", "post", "put", "delete"):
        monkeypatch.setattr(requests, method, fake(method.upper()))
    return log, answers


def test_staff_make_list_and_revoke_codes(calls):
    log, answers = calls
    access = make()
    answers[("POST", "http://home.example:7575/api/v1/server/invites")] = Reply(201, {"invite": {"code": "ABCD-EFGH-JKMN"}})
    answers[("GET", "http://home.example:7575/api/v1/server/invites")] = Reply(200, {"invites": [{"code": "ABCD-EFGH-JKMN", "state": "active"}]})

    assert access.create_invite(note="launch", max_uses=5)["code"] == "ABCD-EFGH-JKMN"
    assert log[-1][2]["json"] == {"auth_token": "tok", "note": "launch", "max_uses": 5, "expires_in_hours": None}
    assert access.list_invites()[0]["state"] == "active"
    access.revoke_invite("ABCD-EFGH-JKMN")
    assert log[-1][:2] == ("DELETE", "http://home.example:7575/api/v1/server/invites/ABCD-EFGH-JKMN")


def test_staff_decide_requests(calls):
    log, answers = calls
    access = make()
    answers[("GET", "http://home.example:7575/api/v1/server/join-requests")] = Reply(200, {"requests": [{"request_id": "r1"}], "pending": 1})
    assert access.list_join_requests() == {"requests": [{"request_id": "r1"}], "pending": 1}
    assert log[-1][2]["params"] == {"auth_token": "tok", "status": "pending"}
    access.approve_join_request("r1")
    assert log[-1][1].endswith("/join-requests/r1/approve")
    access.deny_join_request("r2")
    assert log[-1][1].endswith("/join-requests/r2/deny")


def test_someone_who_is_not_staff_is_told_so(calls):
    _, answers = calls
    answers[("GET", "http://home.example:7575/api/v1/server/invites")] = Reply(403, {"error_code": "auth.privilege_denied"})
    with pytest.raises(NotAnAdminOrServerOwner):
        make().list_invites()


def test_joining_asks_the_home_server_then_the_server_joined(calls):
    log, answers = calls
    access = make()
    answers[("POST", "http://home.example:7575/api/v1/federation/assertions")] = Reply(200, {"assertion": "a.b"})
    answers[("POST", "http://away.example:7575/api/v1/federation/join")] = Reply(200, {"status": "joined", "auth_token": "away-token"})

    result = access.join_server("http://away.example:7575", invite_code="ABCD-EFGH-JKMN", message="hi")

    assert result["auth_token"] == "away-token"
    (_, assertion_url, assertion_call), (_, join_url, join_call) = log
    assert assertion_url == "http://home.example:7575/api/v1/federation/assertions"
    assert assertion_call["json"] == {"auth_token": "tok", "audience": "away.example:7575"}
    assert join_url == "http://away.example:7575/api/v1/federation/join"
    assert join_call["json"] == {"assertion": "a.b", "invite_code": "ABCD-EFGH-JKMN", "message": "hi"}


def test_a_request_that_waits_comes_back_pending_and_can_be_checked(calls):
    _, answers = calls
    access = make()
    answers[("POST", "http://home.example:7575/api/v1/federation/assertions")] = Reply(200, {"assertion": "a.b"})
    answers[("POST", "http://away.example:7575/api/v1/federation/join")] = Reply(202, {"status": "pending", "request_id": "r1"})
    answers[("POST", "http://away.example:7575/api/v1/federation/join/status")] = Reply(202, {"status": "pending", "request_id": "r1"})

    assert access.join_server("http://away.example:7575")["status"] == "pending"
    assert access.check_join_request("http://away.example:7575")["status"] == "pending"


@pytest.mark.parametrize(
    "code, error",
    [
        ("join.invite_invalid", InviteInvalid),
        ("auth.membership_denied", JoinDenied),
        ("auth.membership_pending", JoinPending),
        ("join.assertion_invalid", JoinRefused),
        ("join.refused", JoinRefused),
    ],
)
def test_a_refused_join_raises_what_it_was(calls, code, error):
    _, answers = calls
    answers[("POST", "http://home.example:7575/api/v1/federation/assertions")] = Reply(200, {"assertion": "a.b"})
    answers[("POST", "http://away.example:7575/api/v1/federation/join")] = Reply(403, {"error_code": code})
    with pytest.raises(error):
        make().join_server("http://away.example:7575")


def test_leaving_uses_the_session_of_the_server_left(calls):
    log, _ = calls
    make().leave_server("http://away.example:7575", "away-token")
    assert log[-1][1] == "http://away.example:7575/api/v1/federation/leave"
    assert log[-1][2]["json"] == {"auth_token": "away-token"}


def test_staff_remove_someone_and_let_them_back(calls):
    log, answers = calls
    access = make()
    answers[("POST", "http://home.example:7575/api/v1/server/members/u1/kick")] = Reply(200, {"removed": True})
    assert access.kick_member("u1", reason="spam")["removed"] is True
    assert log[-1][2]["json"] == {"auth_token": "tok", "reason": "spam"}
    access.reinstate_member("u1")
    assert log[-1][1] == "http://home.example:7575/api/v1/server/members/u1/reinstate"


def test_removing_without_the_privilege_is_refused(calls):
    _, answers = calls
    answers[("POST", "http://home.example:7575/api/v1/server/members/u1/kick")] = Reply(403, {"error_code": "auth.privilege_denied"})
    with pytest.raises(NotAnAdminOrServerOwner):
        make().kick_member("u1")
