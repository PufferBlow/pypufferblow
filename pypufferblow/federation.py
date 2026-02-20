__all__ = [
    "Federation",
    "FederationOptions",
]

import requests

from pypufferblow.models.options_model import OptionsModel
from pypufferblow.models.route_model import Route
from pypufferblow.routes import direct_messages_routes, federation_routes



class Federation:
    """
    Federation API wrapper for ActivityPub follow and cross-instance direct messages.
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
        self.auth_token = options.auth_token

    def follow_remote_account(self, remote_handle: str) -> dict:
        """
        Follow a remote ActivityPub account (user@domain).
        """
        payload = {
            "auth_token": self.auth_token,
            "remote_handle": remote_handle,
        }
        response = requests.post(self.FOLLOW_REMOTE_API_ROUTE.api_route, json=payload)
        if response.status_code >= 400:
            raise Exception(
                f"Federation follow failed ({response.status_code}): {response.text}"
            )
        return response.json()

    def send_direct_message(
        self,
        peer: str,
        message: str,
        sent_at: str | None = None,
        attachments: list[str] | None = None,
    ) -> dict:
        """
        Send a direct message to local user or remote handle/actor.
        """
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
        return response.json()

    def load_direct_messages(
        self, peer: str, page: int = 1, messages_per_page: int = 20
    ) -> dict:
        """
        Load direct message conversation with local or remote peer.
        """
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
        return response.json()


class FederationOptions(OptionsModel):
    """
    Federation options.
    """

    def __init__(self, auth_token: str, **kwargs) -> None:
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.auth_token = auth_token
