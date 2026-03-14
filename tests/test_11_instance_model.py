from __future__ import annotations

import logging

from pypufferblow.client import Client, ClientOptions
from pypufferblow.logging_utils import SDK_LOGGER_NAME
from pypufferblow.models.options_model import OptionsModel
from pypufferblow.models.user_model import UserModel
from pypufferblow.system import System, SystemOptions
from pypufferblow.websocket import create_channel_websocket, create_global_websocket


def test_options_model_prefers_instance_url_for_named_domain() -> None:
    options = OptionsModel(instance="https://chat.example.org")

    assert options.scheme == "https"
    assert options.host == "chat.example.org"
    assert options.port is None
    assert options.instance_url == "https://chat.example.org"
    assert options.ws_base_url == "wss://chat.example.org"


def test_options_model_infers_https_for_named_domain() -> None:
    options = OptionsModel(host="chat.example.org")

    assert options.instance_url == "https://chat.example.org:7575"
    assert options.ws_base_url == "wss://chat.example.org:7575"


def test_options_model_keeps_http_for_local_development() -> None:
    options = OptionsModel(host="localhost", port=7575)

    assert options.instance_url == "http://localhost:7575"
    assert options.ws_base_url == "ws://localhost:7575"


def test_options_model_can_enable_verbose_readable_logging() -> None:
    options = OptionsModel(instance="https://chat.example.org", verbose=True)
    sdk_logger = logging.getLogger(SDK_LOGGER_NAME)

    assert options.log_level == "DEBUG"
    assert sdk_logger.level == logging.DEBUG
    assert sdk_logger.handlers


def test_client_routes_are_bound_per_instance() -> None:
    client_a = Client(
        ClientOptions(
            instance="https://alpha.example.org",
            username="alpha",
            password="secret",
        )
    )
    client_b = Client(
        ClientOptions(
            instance="https://beta.example.org",
            username="beta",
            password="secret",
        )
    )

    assert client_a.users.SIGNIN_API_ROUTE.api_route == "https://alpha.example.org/api/v1/users/signin"
    assert client_b.users.SIGNIN_API_ROUTE.api_route == "https://beta.example.org/api/v1/users/signin"


def test_websocket_helpers_follow_instance_scheme() -> None:
    global_ws = create_global_websocket(
        auth_token="token",
        instance="https://chat.example.org",
    )
    channel_ws = create_channel_websocket(
        channel_id="general",
        auth_token="token",
        instance="https://chat.example.org",
    )

    assert global_ws._get_ws_url() == "wss://chat.example.org/ws?auth_token=token"
    assert channel_ws._get_ws_url() == "wss://chat.example.org/ws/channels/general?auth_token=token"


def test_system_instance_aliases_forward_to_server_methods() -> None:
    system = System(SystemOptions(instance="https://chat.example.org", auth_token="token"))

    system.get_server_info = lambda: {"server_name": "Pufferblow"}
    system.get_server_stats = lambda: {"users": 42}
    system.get_server_usage = lambda: {"cpu_percent": 12}
    system.get_server_overview = lambda: {"channels": 7}
    system.get_server_logs = lambda **kwargs: {"lines": kwargs["lines"]}
    system.upload_server_avatar = lambda path: f"avatar:{path}"
    system.upload_server_banner = lambda path: f"banner:{path}"

    assert system.get_instance_info() == {"server_name": "Pufferblow"}
    assert system.get_instance_stats() == {"users": 42}
    assert system.get_instance_usage() == {"cpu_percent": 12}
    assert system.get_instance_overview() == {"channels": 7}
    assert system.get_instance_logs(lines=25) == {"lines": 25}
    assert system.upload_instance_avatar("a.png") == "avatar:a.png"
    assert system.upload_instance_banner("b.png") == "banner:b.png"


def test_system_update_instance_info_accepts_instance_named_aliases() -> None:
    system = System(SystemOptions(instance="https://chat.example.org", auth_token="token"))
    captured_payload: dict = {}

    class FakeResponse:
        status_code = 200

    def fake_put(url, json):
        captured_payload.update(json)
        return FakeResponse()

    import pypufferblow.system as system_module

    original_put = system_module.requests.put
    system_module.requests.put = fake_put
    try:
        system.UPDATE_SERVER_INFO_API_ROUTE = type("RouteLike", (), {"api_route": "https://chat.example.org/api/v1/system/server-info"})()
        system.update_instance_info(
            instance_name="Pufferblow",
            instance_description="Home instance",
            is_private=False,
        )
    finally:
        system_module.requests.put = original_put

    assert captured_payload["server_name"] == "Pufferblow"
    assert captured_payload["server_description"] == "Home instance"
    assert captured_payload["is_private"] is False


def test_user_model_exposes_instance_oriented_aliases() -> None:
    user = UserModel(
        is_owner=True,
        joined_servers_ids=["community-1"],
        origin_server="chat.example.org",
    )

    assert user.is_server_owner is True
    assert user.is_instance_owner is True
    assert user.joined_communities_ids == ["community-1"]
    assert user.origin_instance == "chat.example.org"

    user.is_instance_owner = False
    user.joined_communities_ids = ["community-2"]
    user.origin_instance = "chat2.example.org"

    assert user.is_owner is False
    assert user.joined_servers_ids == ["community-2"]
    assert user.origin_server == "chat2.example.org"
