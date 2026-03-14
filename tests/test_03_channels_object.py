from __future__ import annotations

import asyncio
import logging

import pytest

from pypufferblow.client import Client, ClientOptions
from pypufferblow.exceptions import BadAuthToken, ChannelNotFound
from pypufferblow.models.channel_model import ChannelModel


def create_authenticated_client(mock_sdk_backend) -> Client:
    auth_token = mock_sdk_backend.seed_user(username="user1", password="12345678")
    client = Client(
        ClientOptions(
            instance="https://chat.example.org",
            username="user1",
            password="12345678",
        )
    )
    client.users.user.auth_token = auth_token
    client.channels()
    return client


def test_list_channels(mock_sdk_backend) -> None:
    client = create_authenticated_client(mock_sdk_backend)

    channels = client.channels.list_channels()

    assert isinstance(channels, list)
    assert all(isinstance(channel, ChannelModel) for channel in channels)
    assert channels[0].channel_id == "general"


def test_list_channels_bad_auth_token(mock_sdk_backend) -> None:
    client = create_authenticated_client(mock_sdk_backend)
    client.channels.user.auth_token = "bad-auth-token"

    with pytest.raises(BadAuthToken):
        client.channels.list_channels()


def test_get_channel_info_channel_not_found(mock_sdk_backend) -> None:
    client = create_authenticated_client(mock_sdk_backend)

    with pytest.raises(ChannelNotFound):
        client.channels.get_channel_info("non-existent-channel")


def test_channels_async_wrappers(mock_sdk_backend) -> None:
    client = create_authenticated_client(mock_sdk_backend)

    async def runner() -> tuple[list[ChannelModel], ChannelModel]:
        channels = await client.channels.list_channels_async()
        channel = await client.channels.get_channel_info_async("general")
        return channels, channel

    channels, channel = asyncio.run(runner())

    assert channels[0].channel_id == "general"
    assert channel.channel_name == "general"


def test_channels_verbose_logging_emits_readable_list_and_info_messages(mock_sdk_backend, caplog) -> None:
    client = create_authenticated_client(mock_sdk_backend)
    caplog.set_level(logging.DEBUG, logger="pypufferblow")

    client.channels.list_channels()
    client.channels.get_channel_info("general")

    log_messages = [record.getMessage() for record in caplog.records if record.name.startswith("pypufferblow")]
    assert any("Listing channels on home instance=https://chat.example.org" in message for message in log_messages)
    assert any("Listed 1 channels on home instance=https://chat.example.org" in message for message in log_messages)
    assert any("Fetched channel info channel_id=general channel_name=general" in message for message in log_messages)
