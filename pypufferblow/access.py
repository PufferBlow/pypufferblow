"""Who may join a server: invitation codes, requests to join, and joining another server with your own account.

The first half is for the staff of a server (the owner and moderators): make and revoke invitation codes, and approve or
decline requests to join. The second half is for anyone: join another server with the account you already have, with
no new account and no password there. The home server vouches for you with a short signed statement, and the server
joined answers with its own session, or says the request is waiting for a moderator.
"""

from __future__ import annotations

__all__ = [
    "Access",
    "AccessOptions",
]

import asyncio

import requests

from pypufferblow.exceptions import (
    BadAuthToken,
    InviteInvalid,
    InviteRequired,
    JoinDenied,
    JoinPending,
    JoinRefused,
    NotAnAdminOrServerOwner,
)
from pypufferblow.logging_utils import get_sdk_logger
from pypufferblow.models.options_model import OptionsModel
from pypufferblow.models.route_model import Route
from pypufferblow.routes import access_routes, base_route


class Access:
    """Invitation codes, join requests and joining other servers, through the signed-in account's own server."""

    API_ROUTES: list[Route] = access_routes
    INVITES_API_ROUTE: Route = access_routes[0]
    INVITE_API_ROUTE: Route = access_routes[1]
    JOIN_REQUESTS_API_ROUTE: Route = access_routes[2]
    APPROVE_REQUEST_API_ROUTE: Route = access_routes[3]
    DENY_REQUEST_API_ROUTE: Route = access_routes[4]
    ASSERTIONS_API_ROUTE: Route = access_routes[5]
    JOIN_API_ROUTE: Route = access_routes[6]
    JOIN_STATUS_API_ROUTE: Route = access_routes[7]
    LEAVE_API_ROUTE: Route = access_routes[8]
    KICK_API_ROUTE: Route = access_routes[9]
    REINSTATE_API_ROUTE: Route = access_routes[10]

    def __init__(self, options: AccessOptions) -> None:
        self.options = options
        self.instance_url = options.instance_url
        self.auth_token = options.auth_token
        self.logger = get_sdk_logger("access")

    # -- errors --------------------------------------------------------

    @staticmethod
    def _code(response) -> str:
        try:
            return str(response.json().get("error_code") or "")
        except Exception:
            return ""

    def _check(self, response) -> None:
        """Turn a refusal into the exception that says what was wrong (never quoting a token or a code)."""
        status = response.status_code
        if status < 400:
            return
        code = self._code(response)
        if code == "join.invite_invalid":
            raise InviteInvalid("That invitation code is not valid. It may have expired or been used up.")
        if code == "join.invite_required":
            raise InviteRequired("That server needs an invitation code.")
        if code == "auth.membership_pending":
            raise JoinPending("The request to join is still waiting for a moderator.")
        if code == "auth.membership_denied":
            raise JoinDenied("The request to join was declined, or the membership ended.")
        if code in ("join.refused", "join.assertion_invalid"):
            raise JoinRefused("The server refused the join.")
        if status == 403:
            raise NotAnAdminOrServerOwner("Operation not permitted for this account.")
        if status == 401:
            raise BadAuthToken("The instance rejected the auth token (it is missing, malformed or expired).")
        raise ValueError(f"The instance answered {status}.")

    # -- invitation codes (owner and moderators) ------------------------

    def list_invites(self) -> list[dict]:
        """Every invitation code: ``code, note, max_uses, uses, expires_at, state`` (active, revoked, expired, used_up)."""
        response = requests.get(self.INVITES_API_ROUTE.api_route, params={"auth_token": self.auth_token})
        self._check(response)
        return response.json().get("invites", [])

    def create_invite(self, note: str | None = None, max_uses: int | None = None, expires_in_hours: int | None = None) -> dict:
        """Make a code. With no limits it works for everyone, for ever, until revoked."""
        body = {"auth_token": self.auth_token, "note": note, "max_uses": max_uses, "expires_in_hours": expires_in_hours}
        response = requests.post(self.INVITES_API_ROUTE.api_route, json=body)
        self._check(response)
        return response.json().get("invite", {})

    def revoke_invite(self, code: str) -> dict:
        """End a code now. People already in stay in."""
        response = requests.delete(self.INVITE_API_ROUTE.api_route.format(code=code), params={"auth_token": self.auth_token})
        self._check(response)
        return response.json()

    # -- requests to join (owner and moderators) --------------------------

    def list_join_requests(self, status: str | None = "pending") -> dict:
        """Requests to join: ``{requests, pending}``. ``status`` is ``pending``, ``approved`` or ``denied`` (None: all)."""
        params = {"auth_token": self.auth_token}
        if status:
            params["status"] = status
        response = requests.get(self.JOIN_REQUESTS_API_ROUTE.api_route, params=params)
        self._check(response)
        body = response.json()
        return {"requests": body.get("requests", []), "pending": body.get("pending", 0)}

    def approve_join_request(self, request_id: str) -> dict:
        """Let the person in. Someone from another server is let in the next time they check."""
        response = requests.post(self.APPROVE_REQUEST_API_ROUTE.api_route.format(request_id=request_id), json={"auth_token": self.auth_token})
        self._check(response)
        return response.json()

    def deny_join_request(self, request_id: str) -> dict:
        """Decline the request."""
        response = requests.post(self.DENY_REQUEST_API_ROUTE.api_route.format(request_id=request_id), json={"auth_token": self.auth_token})
        self._check(response)
        return response.json()

    # -- removing people (owner and moderators) ----------------------------

    def kick_member(self, user_id: str, reason: str | None = None) -> dict:
        """Take someone's membership away. Their account stays; they cannot get into this server until reinstated.

        Only the owner can remove another member of staff. Raises ``NotAnAdminOrServerOwner`` without the privilege.
        """
        response = requests.post(self.KICK_API_ROUTE.api_route.format(user_id=user_id), json={"auth_token": self.auth_token, "reason": reason})
        self._check(response)
        return response.json()

    def reinstate_member(self, user_id: str) -> dict:
        """Let someone who was removed back in."""
        response = requests.post(self.REINSTATE_API_ROUTE.api_route.format(user_id=user_id), json={"auth_token": self.auth_token})
        self._check(response)
        return response.json()

    # -- joining other servers with this account ---------------------------

    @staticmethod
    def _target(instance: str) -> tuple[str, str]:
        """The base address to call and the name the server goes by (``host:port``), from ``host``, ``host:port`` or a URL."""
        base = OptionsModel(instance=instance).instance_url.rstrip("/")
        return base, base.split("://", 1)[-1]

    def _path(self, route: Route) -> str:
        """A route's path on any server (the table holds it with this server's address in front)."""
        return route.api_route[route.api_route.index(base_route):]

    def _assertion_for(self, audience: str) -> str:
        """A one-minute signed statement from this account's own server that this account wants to join ``audience``."""
        response = requests.post(self.ASSERTIONS_API_ROUTE.api_route, json={"auth_token": self.auth_token, "audience": audience})
        self._check(response)
        return response.json()["assertion"]

    def join_server(self, instance: str, invite_code: str | None = None, message: str | None = None) -> dict:
        """Join ``instance`` with this account.

        Returns ``{"status": "joined", "auth_token", "refresh_token", "user"}`` (a session on that server), or
        ``{"status": "pending", "request_id"}`` when a moderator has to approve; ask again with
        :meth:`check_join_request`. Give a full URL (``http://host:7575``) for a server that is not on ``https``.
        Raises ``InviteInvalid`` for a bad code, ``JoinDenied`` if declined, ``JoinRefused`` if the server will not
        have you.
        """
        base, name = self._target(instance)
        body = {"assertion": self._assertion_for(name), "invite_code": invite_code or None, "message": message or None}
        response = requests.post(f"{base}{self._path(self.JOIN_API_ROUTE)}", json=body)
        self._check(response)
        return response.json()

    def check_join_request(self, instance: str) -> dict:
        """Ask again about a request that was waiting: a session once approved, ``{"status": "pending"}`` while it waits."""
        base, name = self._target(instance)
        response = requests.post(f"{base}{self._path(self.JOIN_STATUS_API_ROUTE)}", json={"assertion": self._assertion_for(name)})
        self._check(response)
        return response.json()

    def leave_server(self, instance: str, session_token: str) -> dict:
        """Give up a membership. ``session_token`` is the ``auth_token`` that server gave when you joined."""
        base, _name = self._target(instance)
        response = requests.post(f"{base}{self._path(self.LEAVE_API_ROUTE)}", json={"auth_token": session_token})
        self._check(response)
        return response.json()

    # -- async wrappers ----------------------------------------------------

    async def list_invites_async(self) -> list[dict]:
        return await asyncio.to_thread(self.list_invites)

    async def create_invite_async(self, note: str | None = None, max_uses: int | None = None, expires_in_hours: int | None = None) -> dict:
        return await asyncio.to_thread(self.create_invite, note, max_uses, expires_in_hours)

    async def revoke_invite_async(self, code: str) -> dict:
        return await asyncio.to_thread(self.revoke_invite, code)

    async def list_join_requests_async(self, status: str | None = "pending") -> dict:
        return await asyncio.to_thread(self.list_join_requests, status)

    async def approve_join_request_async(self, request_id: str) -> dict:
        return await asyncio.to_thread(self.approve_join_request, request_id)

    async def deny_join_request_async(self, request_id: str) -> dict:
        return await asyncio.to_thread(self.deny_join_request, request_id)

    async def kick_member_async(self, user_id: str, reason: str | None = None) -> dict:
        return await asyncio.to_thread(self.kick_member, user_id, reason)

    async def reinstate_member_async(self, user_id: str) -> dict:
        return await asyncio.to_thread(self.reinstate_member, user_id)

    async def join_server_async(self, instance: str, invite_code: str | None = None, message: str | None = None) -> dict:
        return await asyncio.to_thread(self.join_server, instance, invite_code, message)

    async def check_join_request_async(self, instance: str) -> dict:
        return await asyncio.to_thread(self.check_join_request, instance)

    async def leave_server_async(self, instance: str, session_token: str) -> dict:
        return await asyncio.to_thread(self.leave_server, instance, session_token)


class AccessOptions(OptionsModel):
    """Access options."""

    def __init__(self, auth_token: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.auth_token = auth_token
