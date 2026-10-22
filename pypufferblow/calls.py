from __future__ import annotations

__all__ = [
    "Calls",
    "CallsOptions",
]

import asyncio

import requests

from pypufferblow.exceptions import BadAuthToken, CallBusy, CallRefused, UserNotFound
from pypufferblow.logging_utils import get_sdk_logger
from pypufferblow.models.options_model import OptionsModel
from pypufferblow.models.route_model import Route
from pypufferblow.routes import calls_routes


class Calls:
    """
    1:1 voice calls and the identity keys that make them end-to-end encrypted.

    The instance only relays the set-up messages of a call (and stores public keys); the audio, the
    signatures and the encryption are the clients' business. A bot has no use for the media itself, but
    can ring, answer and relay signals, which is what this wraps.
    """

    API_ROUTES: list[Route] = calls_routes
    INVITE_API_ROUTE: Route = calls_routes[0]
    ACCEPT_API_ROUTE: Route = calls_routes[1]
    REJECT_API_ROUTE: Route = calls_routes[2]
    END_API_ROUTE: Route = calls_routes[3]
    SIGNAL_API_ROUTE: Route = calls_routes[4]
    FALLBACK_API_ROUTE: Route = calls_routes[5]
    IDENTITY_KEYS_API_ROUTE: Route = calls_routes[6]
    IDENTITY_KEY_API_ROUTE: Route = calls_routes[7]

    def __init__(self, options: CallsOptions) -> None:
        self.options = options
        self.auth_token = options.auth_token
        self.instance_url = options.instance_url
        self.logger = get_sdk_logger("calls")

    # ── errors ──────────────────────────────────────────────────

    @staticmethod
    def _detail(response) -> str:
        try:
            body = response.json()
        except Exception:
            return ""
        return str(body.get("detail") or body.get("message") or "")

    def _check(self, response) -> None:
        """Turn a refusal into the exception that says what was wrong (never quoting the token)."""
        status = response.status_code
        if status < 400:
            return
        detail = self._detail(response)
        if status in (401, 403):
            raise BadAuthToken("The instance rejected the auth token (it is missing, malformed or expired).")
        if status == 404:
            raise UserNotFound(detail or "That user or call does not exist.")
        if status == 409:
            raise CallBusy(detail or "You cannot start a call right now.")
        raise CallRefused(detail or f"The instance answered {status}.", status)

    # ── calls ───────────────────────────────────────────────────

    def invite(self, callee_id: str) -> dict:
        """
        Ring someone. Returns ``{call_id, status, ice_servers, ...}``.

        Raises:
            UserNotFound: There is no such user.
            CallBusy: You are already on a call, or rang this person a moment ago. (Whether the *other*
                person is on a call is not reported: they are not rung and the call rings out.)
            CallRefused: Either of you has blocked the other, or you tried to call yourself.
        """
        response = requests.post(self.INVITE_API_ROUTE.api_route.format(callee_id=callee_id), json={"auth_token": self.auth_token, "callee_id": callee_id})
        self._check(response)
        return response.json()

    def accept(self, call_id: str) -> dict:
        """Answer a call you were rung for. Returns ``{status: "accepted", ice_servers}``."""
        return self._action(self.ACCEPT_API_ROUTE, call_id)

    def reject(self, call_id: str) -> dict:
        """Decline a call, or cancel one that is still ringing."""
        return self._action(self.REJECT_API_ROUTE, call_id)

    def end(self, call_id: str) -> dict:
        """End a call."""
        return self._action(self.END_API_ROUTE, call_id)

    def _action(self, route: Route, call_id: str) -> dict:
        response = requests.post(route.api_route.format(call_id=call_id), json={"auth_token": self.auth_token})
        self._check(response)
        return response.json()

    def signal(self, call_id: str, signal_type: str, payload: dict) -> None:
        """
        Relay one set-up message to the other person: ``offer``, ``answer``, ``candidate`` or ``relay``.
        Only once the call has been accepted; the payload may weigh at most 32 KB.
        """
        response = requests.post(
            self.SIGNAL_API_ROUTE.api_route.format(call_id=call_id),
            json={"auth_token": self.auth_token, "signal_type": signal_type, "payload": payload},
        )
        self._check(response)

    def join_relay(self, call_id: str, quality_profile: str = "balanced") -> dict:
        """Join the media-server session for a call that cannot connect directly (``session_id``, ``join_token``, ``signaling_url``)."""
        response = requests.post(
            self.FALLBACK_API_ROUTE.api_route.format(call_id=call_id),
            json={"auth_token": self.auth_token, "quality_profile": quality_profile},
        )
        self._check(response)
        return response.json()

    # ── identity keys ───────────────────────────────────────────

    def register_identity_key(self, public_key: dict, label: str | None = None) -> dict:
        """
        Register the public half of a P-256 signing key (a JWK with ``kty``, ``crv``, ``x``, ``y``).
        Returns ``{created, key}``. Idempotent. Raises ``CallRefused`` for a key that is invalid, a private
        key, held by another account, or when you already have 10.
        """
        response = requests.put(self.IDENTITY_KEYS_API_ROUTE.api_route, json={"auth_token": self.auth_token, "public_key": public_key, "label": label})
        self._check(response)
        return response.json()

    def list_identity_keys(self, user_id: str) -> list[dict]:
        """A person's registered keys, oldest first: ``{key_id, public_key, label, created_at}``."""
        response = requests.get(self.IDENTITY_KEY_API_ROUTE.api_route.format(id=user_id), params={"auth_token": self.auth_token})
        self._check(response)
        return response.json().get("keys", [])

    def remove_identity_key(self, key_id: str) -> None:
        """Remove one of your own keys."""
        response = requests.delete(self.IDENTITY_KEY_API_ROUTE.api_route.format(id=key_id), params={"auth_token": self.auth_token})
        self._check(response)

    async def invite_async(self, callee_id: str) -> dict:
        return await asyncio.to_thread(self.invite, callee_id)


class CallsOptions(OptionsModel):
    """Calls options."""

    def __init__(self, auth_token: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.auth_token = auth_token
