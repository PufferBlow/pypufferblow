from __future__ import annotations

__all__ = [
    "Federation",
    "FederationOptions",
]

import asyncio
import requests

from pypufferblow.exceptions import (
    BadAuthToken,
    InvalidPeerValue,
    NotAnAdminOrServerOwner,
    PeerAlreadyExists,
    PeerNotFound,
)
from pypufferblow.logging_utils import get_sdk_logger
from pypufferblow.models.options_model import OptionsModel
from pypufferblow.models.route_model import Route
from pypufferblow.routes import direct_messages_routes, federation_routes



class Federation:
    """
    Federation API wrapper for ActivityPub follow and cross-instance direct messages.

    These operations are always performed through the authenticated home
    instance, which acts as the local authority for federation.
    """

    API_ROUTES: list[Route] = [*federation_routes, *direct_messages_routes]
    FOLLOW_REMOTE_API_ROUTE: Route = federation_routes[0]
    PEERS_API_ROUTE: Route = federation_routes[1]
    MODE_API_ROUTE: Route = federation_routes[2]
    PEER_API_ROUTE: Route = federation_routes[3]
    PEER_STATUS_API_ROUTE: Route = federation_routes[4]
    PEER_POLICY_API_ROUTE: Route = federation_routes[5]
    PEER_REFRESH_API_ROUTE: Route = federation_routes[6]
    PEERS_IMPORT_API_ROUTE: Route = federation_routes[7]
    SEND_DIRECT_MESSAGE_API_ROUTE: Route = direct_messages_routes[0]
    LOAD_DIRECT_MESSAGES_API_ROUTE: Route = direct_messages_routes[1]

    def __init__(self, options: FederationOptions) -> None:
        """Initialize the instance."""
        self.options = options
        self.host = options.host
        self.port = options.port
        self.instance = options.instance_url
        self.instance_url = options.instance_url
        self.auth_token = options.auth_token
        self.logger = get_sdk_logger("federation")

    # -- peers (admins and the owner) --------------------------------

    def _check_peer(self, response, host: str | None = None) -> None:
        """Turn a refusal into the exception that says what was wrong (never quoting the token)."""
        status = response.status_code
        if status < 400:
            return
        if status == 403:
            raise NotAnAdminOrServerOwner("Operation not permitted for this account.")
        if status == 404:
            raise PeerNotFound(f"{host or 'That instance'} is not a peer.")
        if status == 409:
            raise PeerAlreadyExists(f"{host or 'That instance'} is already a peer.")
        if status == 401:
            raise BadAuthToken("The instance rejected the auth token (it is missing, malformed or expired).")
        if status in (400, 422):
            try:
                details = response.json().get("details") or {}
            except Exception:
                details = {}
            raise InvalidPeerValue("The instance rejected the value.", details.get("field"))
        raise ValueError(f"The instance answered {status}.")

    def list_peers(self) -> dict:
        """The federation mode, how many peers are in each status, and every peer: ``{mode, modes, counts, peers}``."""
        response = requests.get(self.PEERS_API_ROUTE.api_route, params={"auth_token": self.auth_token})
        self._check_peer(response)
        body = response.json()
        return {key: body.get(key) for key in ("mode", "modes", "counts", "peers")}

    def set_federation_mode(self, mode: str) -> str:
        """Set the mode: ``open``, ``allowlist`` or ``closed``."""
        response = requests.put(self.MODE_API_ROUTE.api_route, json={"auth_token": self.auth_token, "mode": mode})
        self._check_peer(response)
        return response.json().get("mode", mode)

    def add_peer(self, host: str, status: str = "federating") -> dict:
        """Add an instance by hand. ``PeerAlreadyExists`` if it is already a peer."""
        response = requests.post(self.PEERS_API_ROUTE.api_route, json={"auth_token": self.auth_token, "host": host, "status": status})
        self._check_peer(response, host)
        return response.json().get("peer", {})

    def set_peer_status(self, host: str, status: str) -> dict:
        """Accept (``federating``), ``limited``, ``blocked`` or ``pending`` for a peer."""
        response = requests.put(self.PEER_STATUS_API_ROUTE.api_route.format(host=host), json={"auth_token": self.auth_token, "status": status})
        self._check_peer(response, host)
        return response.json().get("peer", {})

    def block_peer(self, host: str) -> dict:
        return self.set_peer_status(host, "blocked")

    def accept_peer(self, host: str) -> dict:
        return self.set_peer_status(host, "federating")

    def set_peer_policy(self, host: str, **switches: bool) -> dict:
        """Set some of a peer's switches by hand: ``media``, ``voice``, ``discover`` (True or False)."""
        response = requests.put(self.PEER_POLICY_API_ROUTE.api_route.format(host=host), json={"auth_token": self.auth_token, "policy": switches})
        self._check_peer(response, host)
        return response.json().get("peer", {})

    def remove_peer(self, host: str) -> None:
        """Forget a peer."""
        response = requests.delete(self.PEER_API_ROUTE.api_route.format(host=host), params={"auth_token": self.auth_token})
        self._check_peer(response, host)

    def refresh_peer(self, host: str) -> dict | None:
        """Ask the peer what it is (software, version, users). The peer, or None if it said nothing usable."""
        response = requests.post(self.PEER_REFRESH_API_ROUTE.api_route.format(host=host), json={"auth_token": self.auth_token})
        self._check_peer(response, host)
        body = response.json()
        return body.get("peer") if body.get("found") else None

    def import_peers(self, hosts: list[str], status: str = "blocked") -> dict:
        """Add up to 500 hosts with one status (a shared blocklist). ``{added, skipped, invalid}``."""
        response = requests.post(self.PEERS_IMPORT_API_ROUTE.api_route, json={"auth_token": self.auth_token, "hosts": list(hosts), "status": status})
        self._check_peer(response)
        body = response.json()
        return {key: body.get(key, []) for key in ("added", "skipped", "invalid")}

    def follow_remote_account(self, remote_handle: str) -> dict:
        """
        Follow a remote ActivityPub account (`user@domain`) through the home instance.
        """
        self.logger.info(
            "Following remote account handle=%s via home instance=%s",
            remote_handle,
            self.instance_url,
        )
        payload = {
            "auth_token": self.auth_token,
            "remote_handle": remote_handle,
        }
        response = requests.post(self.FOLLOW_REMOTE_API_ROUTE.api_route, json=payload)
        if response.status_code >= 400:
            raise Exception(
                f"Federation follow failed ({response.status_code}): {response.text}"
            )
        self.logger.info("Followed remote account handle=%s", remote_handle)
        return response.json()

    async def follow_remote_account_async(self, remote_handle: str) -> dict:
        return await asyncio.to_thread(self.follow_remote_account, remote_handle)

    def send_direct_message(
        self,
        peer: str,
        message: str,
        sent_at: str | None = None,
        attachments: list[str] | None = None,
    ) -> dict:
        """
        Send a direct message to a local user or remote ActivityPub handle
        through the home instance.
        """
        self.logger.info(
            "Sending direct message peer=%s via home instance=%s attachments=%s",
            peer,
            self.instance_url,
            len(attachments or []),
        )
        payload = {
            "auth_token": self.auth_token,
            "peer": peer,
            "message": message,
            "sent_at": sent_at,
            "attachments": attachments or [],
        }
        response = requests.post(
            self.SEND_DIRECT_MESSAGE_API_ROUTE.api_route, json=payload
        )
        if response.status_code >= 400:
            raise Exception(
                f"Direct message send failed ({response.status_code}): {response.text}"
            )
        self.logger.debug("Sent direct message peer=%s length=%s", peer, len(message))
        return response.json()

    async def send_direct_message_async(
        self,
        peer: str,
        message: str,
        sent_at: str | None = None,
        attachments: list[str] | None = None,
    ) -> dict:
        return await asyncio.to_thread(
            self.send_direct_message,
            peer,
            message,
            sent_at,
            attachments,
        )

    def load_direct_messages(
        self, peer: str, page: int = 1, messages_per_page: int = 20
    ) -> dict:
        """
        Load direct message conversation with a local or remote peer through the
        home instance.
        """
        self.logger.debug(
            "Loading direct messages peer=%s page=%s messages_per_page=%s",
            peer,
            page,
            messages_per_page,
        )
        params = {
            "auth_token": self.auth_token,
            "peer": peer,
            "page": page,
            "messages_per_page": messages_per_page,
        }
        response = requests.get(self.LOAD_DIRECT_MESSAGES_API_ROUTE.api_route, params=params)
        if response.status_code >= 400:
            raise Exception(
                f"Direct message load failed ({response.status_code}): {response.text}"
            )
        messages = response.json().get("messages", [])
        self.logger.info("Loaded %s direct messages for peer=%s", len(messages), peer)
        return response.json()

    async def load_direct_messages_async(
        self,
        peer: str,
        page: int = 1,
        messages_per_page: int = 20,
    ) -> dict:
        return await asyncio.to_thread(
            self.load_direct_messages,
            peer,
            page,
            messages_per_page,
        )


class FederationOptions(OptionsModel):
    """
    Federation options.
    """

    def __init__(self, auth_token: str, **kwargs) -> None:
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.auth_token = auth_token
