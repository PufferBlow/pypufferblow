__all__ = [
    "DecentralizedAuth",
    "DecentralizedAuthOptions",
]

import requests

from pypufferblow.exceptions import BadAuthToken, ServerError
from pypufferblow.models.options_model import OptionsModel
from pypufferblow.models.route_model import Route
from pypufferblow.routes import decentralized_auth_routes


class DecentralizedAuth:
    API_ROUTES: list[Route] = decentralized_auth_routes

    CHALLENGE_API_ROUTE: Route = decentralized_auth_routes[0]
    VERIFY_API_ROUTE: Route = decentralized_auth_routes[1]
    INTROSPECT_API_ROUTE: Route = decentralized_auth_routes[2]
    REVOKE_API_ROUTE: Route = decentralized_auth_routes[3]

    def __init__(self, options: "DecentralizedAuthOptions") -> None:
        self.options = options
        self.host = options.host
        self.port = options.port
        self.auth_token = options.auth_token

    def issue_challenge(self, node_id: str) -> dict:
        payload = {
            "auth_token": self.auth_token,
            "node_id": node_id,
        }
        response = requests.post(self.CHALLENGE_API_ROUTE.api_route, json=payload)
        if response.status_code in (400, 404):
            raise BadAuthToken("Invalid auth token")
        if response.status_code != 200:
            raise ServerError(f"Failed to issue challenge: {response.text}")
        return response.json()

    def verify_challenge(
        self,
        challenge_id: str,
        node_public_key: str,
        challenge_signature: str,
        shared_secret: str,
    ) -> dict:
        payload = {
            "challenge_id": challenge_id,
            "node_public_key": node_public_key,
            "challenge_signature": challenge_signature,
            "shared_secret": shared_secret,
        }
        response = requests.post(self.VERIFY_API_ROUTE.api_route, json=payload)
        if response.status_code != 200:
            raise ServerError(f"Failed to verify challenge: {response.text}")
        return response.json()

    def introspect_session(self, session_token: str) -> dict:
        payload = {"session_token": session_token}
        response = requests.post(self.INTROSPECT_API_ROUTE.api_route, json=payload)
        if response.status_code != 200:
            raise ServerError(f"Failed to introspect session: {response.text}")
        return response.json()

    def revoke_session(self, session_id: str) -> dict:
        payload = {"auth_token": self.auth_token, "session_id": session_id}
        response = requests.post(self.REVOKE_API_ROUTE.api_route, json=payload)
        if response.status_code in (400, 404):
            raise BadAuthToken("Invalid auth token or session id")
        if response.status_code != 200:
            raise ServerError(f"Failed to revoke session: {response.text}")
        return response.json()


class DecentralizedAuthOptions(OptionsModel):
    def __init__(self, auth_token: str, **kwargs):
        super().__init__(**kwargs)
        self.auth_token = auth_token
