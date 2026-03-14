from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse
from uuid import uuid4

import pytest


class ValueStorage:
    """
    Value storage class for sharing constants across tests cases
    """

    def __init__(self):
        self.username: str = "user1"
        self.password: str = "12345678"
        self.new_username: str = "new_user1"
        self.new_password: str = "123456789"
        self.auth_token: str = None
        self.bad_formated_auth_token: str = "abcdwqwpdopok"


value_storage = ValueStorage()


@dataclass
class MockResponse:
    status_code: int
    payload: dict | None = None
    text: str = ""

    def json(self) -> dict:
        return self.payload or {}


class MockSDKBackend:
    def __init__(self) -> None:
        self.users_by_username: dict[str, dict] = {}
        self.tokens: dict[str, str] = {}
        self.channels: list[dict] = [
            {
                "channel_id": "general",
                "channel_name": "general",
                "messages_ids": [],
                "is_private": False,
                "allowed_users": [],
                "created_at": "2026-03-13T00:00:00Z",
            }
        ]

    def seed_user(
        self,
        *,
        username: str,
        password: str,
        is_owner: bool = False,
        is_admin: bool = False,
        auth_token: str | None = None,
    ) -> str:
        token = auth_token or self._issue_token(username)
        self.users_by_username[username] = {
            "user_id": f"user-{username}",
            "username": username,
            "password": password,
            "status": "ONLINE",
            "last_seen": None,
            "joined_servers_ids": ["community-1"],
            "is_owner": is_owner,
            "is_admin": is_admin,
            "created_at": "2026-03-13T00:00:00Z",
            "updated_at": "2026-03-13T00:00:00Z",
            "auth_token": token,
            "avatar_url": None,
            "banner_url": None,
            "about": None,
            "inbox_id": f"https://chat.example.org/users/{username}/inbox",
            "origin_server": "chat.example.org",
            "roles_ids": [],
        }
        self.tokens[token] = username
        return token

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import requests

        monkeypatch.setattr(requests, "get", self.get)
        monkeypatch.setattr(requests, "post", self.post)
        monkeypatch.setattr(requests, "put", self.put)
        monkeypatch.setattr(requests, "delete", self.delete)

    def get(self, url, params=None, **kwargs):
        path = self._path(url)

        if path.endswith("/api/v1/users/signin"):
            username = (params or {}).get("username")
            password = (params or {}).get("password")
            user = self.users_by_username.get(username)
            if user is None:
                return MockResponse(404, text="username not found")
            if user["password"] != password:
                return MockResponse(401, text="invalid password")
            return MockResponse(200, {"auth_token": user["auth_token"]})

        if path.endswith("/api/v1/users/list"):
            auth_username = self._authenticate((params or {}).get("auth_token"))
            if auth_username is None:
                return MockResponse(400, {"detail": "bad auth token"})
            users = [self._public_user_payload(user) for user in self.users_by_username.values()]
            return MockResponse(200, {"users": users})

        raise AssertionError(f"Unhandled GET request in tests: {url}")

    def post(self, url, json=None, data=None, files=None, **kwargs):
        path = self._path(url)

        if path.endswith("/api/v1/users/signup"):
            username = (json or {}).get("username")
            password = (json or {}).get("password")
            if username in self.users_by_username:
                return MockResponse(409, text="username already exists")
            token = self.seed_user(username=username, password=password)
            return MockResponse(200, {"auth_token": token})

        if path.endswith("/api/v1/users/profile"):
            auth_username = self._authenticate((json or {}).get("auth_token"))
            if auth_username is None:
                return MockResponse(400, {"detail": "bad auth token"})

            target_user_id = (json or {}).get("user_id")
            if target_user_id:
                for user in self.users_by_username.values():
                    if user["user_id"] == target_user_id:
                        return MockResponse(200, {"user_data": self._public_user_payload(user)})
                return MockResponse(404, {"detail": "user not found"})

            user = self.users_by_username[auth_username]
            return MockResponse(200, {"user_data": self._public_user_payload(user)})

        if path.endswith("/api/v1/users/profile/reset-auth-token"):
            auth_token = (json or {}).get("auth_token")
            auth_username = self._authenticate(auth_token)
            if auth_username is None:
                return MockResponse(400, {"detail": "bad auth token"})
            password = (json or {}).get("password")
            user = self.users_by_username[auth_username]
            if user["password"] != password:
                return MockResponse(404, {"detail": "invalid password"})
            new_token = self._issue_token(auth_username)
            user["auth_token"] = new_token
            self.tokens.pop(auth_token, None)
            self.tokens[new_token] = auth_username
            return MockResponse(
                200,
                {
                    "auth_token": new_token,
                    "auth_token_expire_time": "2026-03-14T00:00:00Z",
                },
            )

        if path.endswith("/api/v1/channels/list/"):
            auth_username = self._authenticate((json or {}).get("auth_token"))
            if auth_username is None:
                return MockResponse(400, {"detail": "bad auth token"})
            return MockResponse(200, {"channels": list(self.channels)})

        raise AssertionError(f"Unhandled POST request in tests: {url}")

    def put(self, url, json=None, **kwargs):
        path = self._path(url)

        if path.endswith("/api/v1/users/profile"):
            auth_username = self._authenticate((json or {}).get("auth_token"))
            if auth_username is None:
                return MockResponse(400, {"detail": "bad auth token"})

            user = self.users_by_username[auth_username]

            if "new_username" in (json or {}):
                new_username = json["new_username"]
                if new_username in self.users_by_username and new_username != auth_username:
                    return MockResponse(409, {"detail": "username already exists"})
                self.users_by_username.pop(auth_username)
                user["username"] = new_username
                self.users_by_username[new_username] = user
                self.tokens[user["auth_token"]] = new_username
                return MockResponse(200, {"detail": "username updated"})

            if "status" in (json or {}):
                new_status = json["status"]
                if new_status not in {"ONLINE", "OFFLINE", "INVISIBLE"}:
                    return MockResponse(400, {"detail": "invalid status"})
                user["status"] = new_status
                return MockResponse(200, {"detail": "status updated"})

            if "old_password" in (json or {}) and "new_password" in (json or {}):
                if user["password"] != json["old_password"]:
                    return MockResponse(401, {"detail": "invalid password"})
                user["password"] = json["new_password"]
                return MockResponse(200, {"detail": "password updated"})

            if "about" in (json or {}):
                user["about"] = json["about"]
                return MockResponse(200, {"detail": "about updated"})

            return MockResponse(200, {"detail": "profile updated"})

        raise AssertionError(f"Unhandled PUT request in tests: {url}")

    def delete(self, url, params=None, **kwargs):
        raise AssertionError(f"Unhandled DELETE request in tests: {url}")

    @staticmethod
    def _path(url: str) -> str:
        return urlparse(url).path

    @staticmethod
    def _issue_token(username: str) -> str:
        return f"token-{username}-{uuid4().hex[:8]}"

    def _authenticate(self, auth_token: str | None) -> str | None:
        if not auth_token:
            return None
        return self.tokens.get(auth_token)

    @staticmethod
    def _public_user_payload(user: dict) -> dict:
        return {
            key: value
            for key, value in user.items()
            if key != "password"
        }


@pytest.fixture
def mock_sdk_backend(monkeypatch: pytest.MonkeyPatch) -> MockSDKBackend:
    backend = MockSDKBackend()
    backend.install(monkeypatch)
    return backend
