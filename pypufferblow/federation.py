from __future__ import annotations

__all__ = [
    "Federation",
    "FederationOptions",
]

import asyncio
import requests

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
