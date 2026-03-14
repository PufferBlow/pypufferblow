from __future__ import annotations

import asyncio
import logging
import threading

import pytest

from pypufferblow.bot import Bot, BotCheckFailure, BotOptions
from pypufferblow.models.message_model import WebSocketMessage
from pypufferblow.models.user_model import UserModel


class FakeUsers:
    def __init__(self) -> None:
        self.user = UserModel(auth_token="fake-token", username="bot-user")
        self.is_signed_in = False
        self.sign_in_calls = 0
        self.sign_up_calls = 0

    def sign_in(self) -> str:
        self.sign_in_calls += 1
        self.is_signed_in = True
        return self.user.auth_token

    def sign_up(self) -> str:
        self.sign_up_calls += 1
        self.is_signed_in = True
        return self.user.auth_token


class FakeChannels:
    def __init__(self) -> None:
        self.sent_messages: list[dict] = []
        self.read_receipts: list[dict] = []

    def send_message(self, channel_id: str, message: str, attachments=None) -> None:
        self.sent_messages.append(
            {
                "channel_id": channel_id,
                "message": message,
                "attachments": attachments,
            }
        )

    def mark_message_as_read(self, channel_id: str, message_id: str) -> None:
        self.read_receipts.append(
            {
                "channel_id": channel_id,
                "message_id": message_id,
            }
        )


class FakeWebSocket:
    def __init__(self) -> None:
        self.on_message = None
        self.on_connected = None
        self.on_disconnected = None
        self.on_error = None
        self.connected = False

    def connect(self) -> None:
        self.connected = True
        if self.on_connected:
            self.on_connected()

    def disconnect(self) -> None:
        self.connected = False
        if self.on_disconnected:
            self.on_disconnected("manual-stop")


class FakeClient:
    def __init__(self) -> None:
        self.users = FakeUsers()
        self._channels = FakeChannels()
        self._websocket = FakeWebSocket()

    def channels(self) -> FakeChannels:
        return self._channels

    def websocket(self) -> FakeWebSocket:
        return self._websocket

    def create_channel_websocket(self, channel_id: str) -> FakeWebSocket:
        return self._websocket


def create_bot(*, command_prefix: str = "!") -> tuple[Bot, FakeClient]:
    fake_client = FakeClient()
    bot = Bot(
        BotOptions(
            host="localhost",
            port=7575,
            username="bot-user",
            password="secret",
            command_prefix=command_prefix,
        ),
        client=fake_client,
    )
    return bot, fake_client


def build_message(content: str, *, username: str = "alice") -> WebSocketMessage:
    return WebSocketMessage(
        type="message",
        channel_id="general",
        message_id="msg-1",
        sender_user_id="user-1",
        username=username,
        message=content,
    )


def test_bot_start_authenticates_and_connects_websocket() -> None:
    bot, fake_client = create_bot()

    events: list[str] = []

    @bot.startup()
    def on_startup(ctx):
        events.append(ctx.event_name)

    @bot.connect()
    def on_connect(ctx):
        events.append(ctx.event_name)

    bot.start()

    assert fake_client.users.sign_in_calls == 1
    assert fake_client._websocket.connected is True
    assert events == ["startup", "connect"]


def test_bot_stop_dispatches_disconnect_and_shutdown() -> None:
    bot, _ = create_bot()
    events: list[str] = []

    @bot.disconnect()
    def on_disconnect(ctx):
        events.append(f"{ctx.event_name}:{ctx.reason}")

    @bot.shutdown()
    def on_shutdown(ctx):
        events.append(ctx.event_name)

    bot.start()
    bot.stop()

    assert events[-2:] == ["disconnect:manual-stop", "shutdown"]


def test_started_and_stopped_events_fire_as_full_lifecycle_boundaries() -> None:
    bot, _ = create_bot()
    events: list[str] = []

    @bot.started()
    def on_started(ctx):
        events.append(ctx.event_name)

    @bot.stopped()
    def on_stopped(ctx):
        events.append(ctx.event_name)

    bot.start()
    bot.stop()

    assert events == ["started", "stopped"]


def test_lifecycle_listener_receives_startup_and_shutdown_events() -> None:
    bot, _ = create_bot()
    lifecycle_events: list[str] = []

    @bot.lifecycle()
    def on_lifecycle(ctx):
        lifecycle_events.append(ctx.lifecycle_event)

    bot.start()
    bot.stop()

    assert lifecycle_events == [
        "startup",
        "connect",
        "ready",
        "started",
        "disconnect",
        "shutdown",
        "stopped",
    ]


def test_wait_for_lifecycle_returns_matching_lifecycle_context() -> None:
    bot, _ = create_bot()

    async def runner() -> str:
        waiter = asyncio.create_task(bot.wait_for_lifecycle("started", timeout=1.0))
        await asyncio.sleep(0)
        bot.start()
        context = await waiter
        return context.lifecycle_event or ""

    assert asyncio.run(runner()) == "started"


def test_command_handler_parses_arguments_and_replies() -> None:
    bot, fake_client = create_bot()
    bot.authenticate()

    @bot.command("sum")
    def sum_command(ctx, left: int, right: int):
        ctx.reply(str(left + right))

    bot.process_websocket_message(build_message("!sum 2 3"))

    assert fake_client._channels.sent_messages == [
        {
            "channel_id": "general",
            "message": "5",
            "attachments": None,
        }
    ]


def test_command_handler_supports_alias_bool_and_optional_types() -> None:
    bot, fake_client = create_bot()
    bot.authenticate()

    @bot.command("flag", aliases=("toggle",))
    def flag_command(ctx, enabled: bool, note: str | None = None):
        ctx.reply(f"{enabled}:{note}")

    bot.process_websocket_message(build_message("!toggle yes testing"))

    assert fake_client._channels.sent_messages[-1]["message"] == "True:testing"


def test_message_handler_and_command_can_share_event_stream() -> None:
    bot, fake_client = create_bot()
    bot.authenticate()

    seen_messages: list[str] = []

    @bot.message(startswith="!")
    def on_prefixed_message(ctx):
        seen_messages.append(ctx.content)

    @bot.command("ping")
    def ping(ctx):
        ctx.reply("pong")

    bot.process_websocket_message(build_message("!ping", username="bob"))

    assert seen_messages == ["!ping"]
    assert fake_client._channels.sent_messages[-1]["message"] == "pong"


def test_message_handler_can_ignore_bot_messages() -> None:
    bot, _ = create_bot()
    bot.authenticate()
    seen_messages: list[str] = []

    @bot.message(ignore_bots=True)
    def on_message(ctx):
        seen_messages.append(ctx.content)

    bot.process_websocket_message(build_message("hello from self", username="bot-user"))
    bot.process_websocket_message(build_message("hello from user", username="friend"))

    assert seen_messages == ["hello from user"]


def test_bot_context_can_mark_read() -> None:
    bot, fake_client = create_bot()
    bot.authenticate()

    @bot.command("ack")
    def ack(ctx):
        ctx.mark_read()
        ctx.reply("done")

    bot.process_websocket_message(build_message("!ack"))

    assert fake_client._channels.read_receipts == [
        {
            "channel_id": "general",
            "message_id": "msg-1",
        }
    ]
    assert fake_client._channels.sent_messages[-1]["message"] == "done"


def test_async_command_handler_is_supported() -> None:
    bot, fake_client = create_bot()
    bot.authenticate()

    @bot.command("async")
    async def async_command(ctx):
        await asyncio.sleep(0)
        ctx.reply("async-ok")

    bot.process_websocket_message(build_message("!async"))

    assert fake_client._channels.sent_messages[-1]["message"] == "async-ok"


def test_error_handler_receives_command_binding_errors() -> None:
    bot, _ = create_bot()
    bot.authenticate()
    seen_errors: list[str] = []

    @bot.error()
    def on_error(ctx):
        seen_errors.append(str(ctx.error))

    @bot.command("sum")
    def sum_command(ctx, left: int, right: int):
        ctx.reply(str(left + right))

    bot.process_websocket_message(build_message("!sum 1"))

    assert seen_errors == ["Missing required command argument: right"]


def test_handler_errors_raise_when_no_error_handler_is_registered() -> None:
    bot, _ = create_bot()
    bot.authenticate()

    @bot.command("explode")
    def explode(ctx):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        bot.process_websocket_message(build_message("!explode"))


def test_conditional_listener_only_fires_when_check_matches() -> None:
    bot, _ = create_bot()
    bot.authenticate()
    seen: list[str] = []

    @bot.listen("message", check=lambda ctx: ctx.content.endswith("ok"))
    def on_ok(ctx):
        seen.append(ctx.content)

    bot.process_websocket_message(build_message("not yet"))
    bot.process_websocket_message(build_message("this is ok"))

    assert seen == ["this is ok"]


def test_once_listener_fires_only_once() -> None:
    bot, _ = create_bot()
    bot.authenticate()
    seen: list[str] = []

    @bot.once("message", check=lambda ctx: "ping" in ctx.content)
    def on_ping(ctx):
        seen.append(ctx.content)

    bot.process_websocket_message(build_message("ping-1"))
    bot.process_websocket_message(build_message("ping-2"))

    assert seen == ["ping-1"]


def test_wait_for_returns_matching_event_context() -> None:
    bot, _ = create_bot()
    bot.authenticate()

    async def runner() -> str:
        waiter = asyncio.create_task(
            bot.wait_for(
                "message",
                check=lambda ctx: ctx.content == "!ready",
                timeout=1.0,
            )
        )
        await asyncio.sleep(0)
        bot.process_websocket_message(build_message("ignore"))
        bot.process_websocket_message(build_message("!ready"))
        context = await waiter
        return context.content

    assert asyncio.run(runner()) == "!ready"


def test_wait_until_ready_resolves_after_ready_event() -> None:
    bot, _ = create_bot()

    async def runner() -> bool:
        waiter = asyncio.create_task(bot.wait_until_ready(timeout=1.0))
        await asyncio.sleep(0)
        bot.start()
        await waiter
        return bot._ready

    assert asyncio.run(runner()) is True


def test_before_and_after_command_hooks_fire_around_command() -> None:
    bot, fake_client = create_bot()
    bot.authenticate()
    order: list[str] = []

    @bot.before_command()
    def before(ctx):
        order.append(f"before:{ctx.command_name}")

    @bot.after_command()
    def after(ctx):
        order.append(f"after:{ctx.command_name}:{ctx.error is None}")

    @bot.command("ping")
    def ping(ctx):
        order.append("command:ping")
        ctx.reply("pong")

    bot.process_websocket_message(build_message("!ping"))

    assert order == ["before:ping", "command:ping", "after:ping:True"]
    assert fake_client._channels.sent_messages[-1]["message"] == "pong"


def test_command_checks_block_execution_and_emit_error() -> None:
    bot, fake_client = create_bot()
    bot.authenticate()
    seen_errors: list[str] = []

    @bot.error()
    def on_error(ctx):
        seen_errors.append(type(ctx.error).__name__)

    @bot.check(lambda ctx: ctx.author_name == "allowed-user")
    @bot.command("ping")
    def ping(ctx):
        ctx.reply("pong")

    bot.process_websocket_message(build_message("!ping", username="blocked-user"))

    assert fake_client._channels.sent_messages == []
    assert seen_errors == ["BotCheckFailure"]


def test_command_cooldown_blocks_repeated_calls() -> None:
    bot, fake_client = create_bot()
    bot.authenticate()
    seen_errors: list[str] = []

    @bot.error()
    def on_error(ctx):
        seen_errors.append(type(ctx.error).__name__)

    @bot.cooldown(1, 60.0, bucket="user")
    @bot.command("ping")
    def ping(ctx):
        ctx.reply("pong")

    bot.process_websocket_message(build_message("!ping", username="alice"))
    bot.process_websocket_message(build_message("!ping", username="alice"))

    assert len(fake_client._channels.sent_messages) == 1
    assert seen_errors == ["CommandOnCooldown"]


def test_command_group_supports_nested_commands() -> None:
    bot, fake_client = create_bot()
    bot.authenticate()

    admin = bot.group("admin", aliases=("mod",))

    @admin.command("ban", aliases=("block",))
    def ban(ctx, target: str):
        ctx.reply(f"ban:{target}")

    bot.process_websocket_message(build_message("!admin ban user-1"))
    bot.process_websocket_message(build_message("!mod block user-2"))

    assert fake_client._channels.sent_messages[-2]["message"] == "ban:user-1"
    assert fake_client._channels.sent_messages[-1]["message"] == "ban:user-2"


def test_command_introspection_and_help_formatting_support_grouped_commands() -> None:
    bot, _ = create_bot()
    admin = bot.group("admin")

    @bot.command("ping", description="Health check", usage="[target]")
    def ping(ctx):
        ctx.reply("pong")

    @admin.command("ban", description="Ban a user", usage="<user_id>")
    def ban(ctx, user_id: str):
        ctx.reply(user_id)

    registration = bot.get_command("admin ban")
    help_text = bot.format_help("admin ban")
    summary = bot.format_help()

    assert registration is not None
    assert registration.name == "admin ban"
    assert "Command: !admin ban" in help_text
    assert "Usage: !admin ban <user_id>" in help_text
    assert "!ping [target] - Health check" in summary
    assert "!admin ban <user_id> - Ban a user" in summary


def test_hidden_commands_are_excluded_from_default_help() -> None:
    bot, _ = create_bot()

    @bot.command("visible", description="Visible command")
    def visible(ctx):
        ctx.reply("ok")

    @bot.command("hidden", description="Secret command", hidden=True)
    def hidden(ctx):
        ctx.reply("secret")

    public_help = bot.format_help()
    private_help = bot.format_help(include_hidden=True)

    assert "!visible - Visible command" in public_help
    assert "!hidden - Secret command" not in public_help
    assert "!hidden - Secret command" in private_help


def test_installed_help_command_replies_with_general_and_specific_help() -> None:
    bot, fake_client = create_bot()
    bot.authenticate()

    @bot.command("ping", description="Health check", usage="[target]")
    def ping(ctx):
        ctx.reply("pong")

    bot.install_help_command()

    bot.process_websocket_message(build_message("!help"))
    bot.process_websocket_message(build_message("!help ping"))

    assert "Available commands:" in fake_client._channels.sent_messages[-2]["message"]
    assert "!ping [target] - Health check" in fake_client._channels.sent_messages[-2]["message"]
    assert "Command: !ping" in fake_client._channels.sent_messages[-1]["message"]
    assert "Usage: !ping [target]" in fake_client._channels.sent_messages[-1]["message"]


def test_longer_group_command_wins_over_shorter_prefix_command() -> None:
    bot, fake_client = create_bot()
    bot.authenticate()
    admin = bot.group("admin")

    @bot.command("admin")
    def admin_root(ctx):
        ctx.reply("root")

    @admin.command("ping")
    def admin_ping(ctx):
        ctx.reply("group-ping")

    bot.process_websocket_message(build_message("!admin ping"))

    assert fake_client._channels.sent_messages[-1]["message"] == "group-ping"


def test_reset_command_cooldown_allows_command_to_run_again() -> None:
    bot, fake_client = create_bot()
    bot.authenticate()
    seen_errors: list[str] = []

    @bot.error()
    def on_error(ctx):
        seen_errors.append(type(ctx.error).__name__)

    @bot.cooldown(1, 60.0, bucket="user")
    @bot.command("ping")
    def ping(ctx):
        ctx.reply("pong")

    bot.process_websocket_message(build_message("!ping", username="alice"))
    bot.process_websocket_message(build_message("!ping", username="alice"))
    assert seen_errors == ["CommandOnCooldown"]

    removed = bot.reset_command_cooldown("ping", bucket_key="user-1")
    bot.process_websocket_message(build_message("!ping", username="alice"))

    assert removed == 1
    assert [message["message"] for message in fake_client._channels.sent_messages] == ["pong", "pong"]


def test_loop_task_autostarts_after_bot_is_ready() -> None:
    bot, _ = create_bot()
    loop_seen = threading.Event()
    loop_iterations: list[int] = []

    @bot.loop(seconds=0.01, count=1)
    def heartbeat(ctx):
        loop_iterations.append(ctx.bot._ready)
        loop_seen.set()

    bot.start()
    assert loop_seen.wait(0.5) is True
    bot.stop()

    assert loop_iterations == [True]


def test_loop_task_can_be_started_and_stopped_manually() -> None:
    bot, _ = create_bot()
    loop_seen = threading.Event()
    loop_iterations: list[int] = []

    @bot.loop(seconds=0.01, wait_until_ready=False, autostart=False)
    def heartbeat(ctx):
        loop_iterations.append(1)
        loop_seen.set()

    heartbeat.start()
    assert loop_seen.wait(0.5) is True
    heartbeat.stop()

    assert len(loop_iterations) >= 1
    assert heartbeat.is_running is False


def test_loop_task_before_and_after_hooks_fire_around_iteration() -> None:
    bot, _ = create_bot()
    loop_seen = threading.Event()
    order: list[str] = []

    @bot.loop(seconds=0.01, count=1, wait_until_ready=False)
    def heartbeat(ctx):
        order.append("loop")
        loop_seen.set()

    @heartbeat.before_loop()
    def before(ctx):
        order.append("before")

    @heartbeat.after_loop()
    def after(ctx):
        order.append(f"after:{ctx.error is None}")

    heartbeat.start()
    assert loop_seen.wait(0.5) is True
    heartbeat.stop()

    assert order == ["before", "loop", "after:True"]


def test_loop_task_error_handler_receives_loop_failure() -> None:
    bot, _ = create_bot()
    loop_seen = threading.Event()
    seen_errors: list[str] = []

    @bot.loop(seconds=0.01, count=1, wait_until_ready=False)
    def heartbeat(ctx):
        raise RuntimeError("loop-boom")

    @heartbeat.on_error()
    def on_loop_error(ctx):
        seen_errors.append(str(ctx.error))
        loop_seen.set()

    heartbeat.start()
    assert loop_seen.wait(0.5) is True
    heartbeat.stop()

    assert seen_errors == ["loop-boom"]


def test_async_context_manager_starts_and_stops_bot() -> None:
    bot, fake_client = create_bot()

    async def runner() -> tuple[bool, bool]:
        async with bot as running_bot:
            return running_bot._running, fake_client._websocket.connected

    running, connected = asyncio.run(runner())

    assert running is True
    assert connected is True
    assert bot._running is False
    assert fake_client._websocket.connected is False


def test_verbose_bot_logging_emits_readable_lifecycle_and_command_messages(caplog) -> None:
    bot, _ = create_bot()
    bot.options.verbose = True
    bot.logger.setLevel(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger="pypufferblow")

    @bot.command("ping")
    def ping(ctx):
        ctx.reply("pong")

    bot.start()
    bot.process_websocket_message(build_message("!ping", username="alice"))
    bot.stop()

    log_messages = [record.getMessage() for record in caplog.records if record.name.startswith("pypufferblow")]

    assert any("Starting bot user=bot-user" in message for message in log_messages)
    assert any("Websocket connected; bot is ready" in message for message in log_messages)
    assert any("Matched command name=ping" in message for message in log_messages)
    assert any("Stopping bot user=bot-user" in message for message in log_messages)


def test_async_helpers_delegate_to_sync_operations() -> None:
    bot, fake_client = create_bot()

    async def runner() -> None:
        await bot.authenticate_async()
        await bot.send_message_async("general", "hello async")
        await bot.mark_message_as_read_async("general", "msg-1")

    asyncio.run(runner())

    assert fake_client.users.sign_in_calls == 1
    assert fake_client._channels.sent_messages[-1]["message"] == "hello async"
    assert fake_client._channels.read_receipts[-1]["message_id"] == "msg-1"
