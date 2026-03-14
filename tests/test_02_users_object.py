from __future__ import annotations

import asyncio
import logging
import random

import pytest

from pypufferblow.client import Client, ClientOptions
from pypufferblow.exceptions import (
    BadAuthToken,
    InvalidPassword,
    InvalidStatusValue,
    UsernameAlreadyExists,
    UsernameNotFound,
)
from pypufferblow.models.user_model import UserModel
from pypufferblow.users import USER_STATUS


def create_client(username: str, password: str) -> Client:
    return Client(
        ClientOptions(
            instance="https://chat.example.org",
            username=username,
            password=password,
        )
    )


def test_users_model_sign_up(mock_sdk_backend) -> None:
    client = create_client("user1", "12345678")

    client.users.sign_up()

    assert client.users.user.auth_token.startswith("token-user1-")
    assert client.users.user.username == "user1"


def test_users_model_sign_up_username_already_exists(mock_sdk_backend) -> None:
    mock_sdk_backend.seed_user(username="user1", password="12345678")
    client = create_client("user1", "12345678")

    with pytest.raises(UsernameAlreadyExists):
        client.users.sign_up()


def test_users_model_sign_in(mock_sdk_backend) -> None:
    mock_sdk_backend.seed_user(username="user1", password="12345678")
    client = create_client("user1", "12345678")

    auth_token = client.users.sign_in()

    assert auth_token == client.users.user.auth_token
    assert client.users.user.username == "user1"


def test_users_model_sign_in_username_not_found(mock_sdk_backend) -> None:
    client = create_client("missing-user", "12345678")

    with pytest.raises(UsernameNotFound):
        client.users.sign_in()


def test_users_model_sign_in_invalid_password(mock_sdk_backend) -> None:
    mock_sdk_backend.seed_user(username="user1", password="12345678")
    client = create_client("user1", "wrong-password")

    with pytest.raises(InvalidPassword):
        client.users.sign_in()


def test_users_model_update_username(mock_sdk_backend) -> None:
    auth_token = mock_sdk_backend.seed_user(username="user1", password="12345678")
    client = create_client("user1", "12345678")
    client.users.user.auth_token = auth_token

    client.users.update_username(new_username="new_user1")

    assert client.users.user.username == "new_user1"
    assert "new_user1" in mock_sdk_backend.users_by_username


def test_users_model_update_username_already_exists(mock_sdk_backend) -> None:
    auth_token = mock_sdk_backend.seed_user(username="user1", password="12345678")
    mock_sdk_backend.seed_user(username="new_user1", password="abcdefgh")
    client = create_client("user1", "12345678")
    client.users.user.auth_token = auth_token

    with pytest.raises(UsernameAlreadyExists):
        client.users.update_username(new_username="new_user1")


def test_users_model_update_user_status(mock_sdk_backend) -> None:
    auth_token = mock_sdk_backend.seed_user(username="user1", password="12345678")
    client = create_client("user1", "12345678")
    client.users.user.auth_token = auth_token

    new_status = random.choice(USER_STATUS)
    client.users.update_user_status(new_status=new_status)

    assert client.users.user.status == new_status


def test_users_model_update_user_status_invalid_status_value(mock_sdk_backend) -> None:
    auth_token = mock_sdk_backend.seed_user(username="user1", password="12345678")
    client = create_client("user1", "12345678")
    client.users.user.auth_token = auth_token

    with pytest.raises(InvalidStatusValue):
        client.users.update_user_status(new_status="NOT_VALID_STATUS")


def test_users_model_update_user_password(mock_sdk_backend) -> None:
    auth_token = mock_sdk_backend.seed_user(username="user1", password="12345678")
    client = create_client("user1", "12345678")
    client.users.user.auth_token = auth_token

    client.users.update_user_password(
        old_password="12345678",
        new_password="123456789",
    )

    assert mock_sdk_backend.users_by_username["user1"]["password"] == "123456789"


def test_users_model_update_user_password_invalid_password(mock_sdk_backend) -> None:
    auth_token = mock_sdk_backend.seed_user(username="user1", password="12345678")
    client = create_client("user1", "12345678")
    client.users.user.auth_token = auth_token

    with pytest.raises(InvalidPassword):
        client.users.update_user_password(
            old_password="wrong-old-password",
            new_password="123456789",
        )


def test_users_model_reset_user_auth_token(mock_sdk_backend) -> None:
    auth_token = mock_sdk_backend.seed_user(username="user1", password="12345678")
    client = create_client("user1", "12345678")
    client.users.user.auth_token = auth_token

    client.users.reset_user_auth_token()

    assert client.users.user.auth_token != auth_token
    assert client.users.user.auth_token_expire_time == "2026-03-14T00:00:00Z"


def test_users_model_reset_user_auth_token_invalid_password(mock_sdk_backend) -> None:
    auth_token = mock_sdk_backend.seed_user(username="user1", password="12345678")
    client = create_client("user1", "wrong-password")
    client.users.user.auth_token = auth_token

    with pytest.raises(InvalidPassword):
        client.users.reset_user_auth_token()


def test_users_model_reset_user_auth_token_bad_auth_token(mock_sdk_backend) -> None:
    mock_sdk_backend.seed_user(username="user1", password="12345678")
    client = create_client("user1", "12345678")
    client.users.user.auth_token = "bad-auth-token"

    with pytest.raises(BadAuthToken):
        client.users.reset_user_auth_token()


def test_users_list_users(mock_sdk_backend) -> None:
    auth_token = mock_sdk_backend.seed_user(username="user1", password="12345678")
    mock_sdk_backend.seed_user(username="user2", password="abcdefgh")
    client = create_client("user1", "12345678")
    client.users.user.auth_token = auth_token

    users = client.users.list_users()

    assert isinstance(users, list)
    assert all(isinstance(user, UserModel) for user in users)
    assert {user.username for user in users} == {"user1", "user2"}


def test_users_list_users_bad_auth_token(mock_sdk_backend) -> None:
    mock_sdk_backend.seed_user(username="user1", password="12345678")
    client = create_client("user1", "12345678")
    client.users.user.auth_token = "bad-auth-token"

    with pytest.raises(BadAuthToken):
        client.users.list_users()


def test_users_async_wrappers(mock_sdk_backend) -> None:
    mock_sdk_backend.seed_user(username="user1", password="12345678")
    mock_sdk_backend.seed_user(username="user2", password="abcdefgh")
    client = create_client("user1", "12345678")

    async def runner() -> tuple[str, list[UserModel]]:
        auth_token = await client.users.sign_in_async()
        users = await client.users.list_users_async()
        return auth_token, users

    auth_token, users = asyncio.run(runner())

    assert auth_token == client.users.user.auth_token
    assert {user.username for user in users} == {"user1", "user2"}


def test_users_verbose_logging_emits_readable_auth_and_list_messages(mock_sdk_backend, caplog) -> None:
    mock_sdk_backend.seed_user(username="user1", password="12345678")
    mock_sdk_backend.seed_user(username="user2", password="abcdefgh")
    client = Client(
        ClientOptions(
            instance="https://chat.example.org",
            username="user1",
            password="12345678",
            verbose=True,
        )
    )
    caplog.set_level(logging.DEBUG, logger="pypufferblow")

    client.users.sign_in()
    client.users.list_users()

    log_messages = [record.getMessage() for record in caplog.records if record.name.startswith("pypufferblow")]
    assert any("Signing in username=user1 on home instance=https://chat.example.org" in message for message in log_messages)
    assert any("Signed in username=user1" in message for message in log_messages)
    assert any("Listed 2 users on home instance=https://chat.example.org" in message for message in log_messages)
