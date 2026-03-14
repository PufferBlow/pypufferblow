from __future__ import annotations

__all__ = [
    "Bot",
    "BotContext",
    "BotOptions",
    "CommandRegistration",
    "CommandGroup",
    "MessageRegistration",
    "ConditionalEventRegistration",
    "LoopTask",
    "BotCheckFailure",
    "CommandOnCooldown",
]

LIFECYCLE_EVENTS = {
    "startup",
    "connect",
    "ready",
    "started",
    "disconnect",
    "shutdown",
    "stopped",
    "error",
}

import asyncio
import inspect
import shlex
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from types import UnionType
from typing import Any, Callable, Iterable, Union, get_args, get_origin, get_type_hints

from pypufferblow.client import Client, ClientOptions
from pypufferblow.logging_utils import get_sdk_logger
from pypufferblow.models.message_model import WebSocketMessage


Handler = Callable[..., Any]
Predicate = Callable[..., Any]


class BotCheckFailure(Exception):
    """Raised when a command check blocks command execution."""


class CommandOnCooldown(Exception):
    """Raised when a command is rate-limited by a cooldown."""

    def __init__(self, retry_after: float) -> None:
        super().__init__(f"Command is on cooldown for {retry_after:.2f}s")
        self.retry_after = retry_after


@dataclass(slots=True)
class CommandRegistration:
    name: str
    handler: Handler
    aliases: tuple[str, ...] = ()
    prefix: str | None = None
    description: str | None = None
    usage: str | None = None
    hidden: bool = False
    case_sensitive: bool = False
    cooldown: tuple[int, float, str] | None = None


@dataclass(slots=True)
class MessageRegistration:
    handler: Handler
    startswith: str | None = None
    contains: str | None = None
    channel_id: str | None = None
    ignore_bots: bool = False


@dataclass(slots=True)
class ConditionalEventRegistration:
    event_name: str
    handler: Handler
    check: Predicate | None = None
    once: bool = False


@dataclass(slots=True)
class EventWaiter:
    event_name: str
    future: asyncio.Future
    loop: asyncio.AbstractEventLoop
    check: Predicate | None = None


class CommandGroup:
    """
    Command namespace helper for grouped commands like `!admin ban`.
    """

    def __init__(
        self,
        bot: Bot,
        name: str,
        *,
        aliases: Iterable[str] | None = None,
        prefix: str | None = None,
        description: str | None = None,
        case_sensitive: bool = False,
    ) -> None:
        self.bot = bot
        self.name = name.strip()
        self.aliases = tuple(alias.strip() for alias in (aliases or ()) if alias.strip())
        self.prefix = prefix
        self.description = description
        self.case_sensitive = case_sensitive

    def command(
        self,
        name: str | None = None,
        *,
        aliases: Iterable[str] | None = None,
        prefix: str | None = None,
        description: str | None = None,
        usage: str | None = None,
        hidden: bool = False,
        case_sensitive: bool | None = None,
    ) -> Callable[[Handler], Handler]:
        command_name = (name or "").strip()
        full_name = " ".join(part for part in (self.name, command_name) if part)
        full_aliases: list[str] = []

        for group_alias in self.aliases or ():
            if command_name:
                full_aliases.append(f"{group_alias} {command_name}")
            else:
                full_aliases.append(group_alias)

        for alias in aliases or ():
            clean_alias = alias.strip()
            if clean_alias:
                full_aliases.append(f"{self.name} {clean_alias}")
                for group_alias in self.aliases or ():
                    full_aliases.append(f"{group_alias} {clean_alias}")

        return self.bot.command(
            full_name,
            aliases=tuple(dict.fromkeys(full_aliases)),
            prefix=prefix if prefix is not None else self.prefix,
            description=description or self.description,
            usage=usage,
            hidden=hidden,
            case_sensitive=self.case_sensitive if case_sensitive is None else case_sensitive,
        )

    def group(
        self,
        name: str,
        *,
        aliases: Iterable[str] | None = None,
        prefix: str | None = None,
        description: str | None = None,
        case_sensitive: bool | None = None,
    ) -> CommandGroup:
        nested_name = " ".join(part for part in (self.name, name.strip()) if part)
        nested_aliases: list[str] = []

        for group_alias in self.aliases or ():
            nested_aliases.append(f"{group_alias} {name.strip()}")

        for alias in aliases or ():
            clean_alias = alias.strip()
            if clean_alias:
                nested_aliases.append(f"{self.name} {clean_alias}")
                for group_alias in self.aliases or ():
                    nested_aliases.append(f"{group_alias} {clean_alias}")

        return CommandGroup(
            self.bot,
            nested_name,
            aliases=tuple(dict.fromkeys(nested_aliases)),
            prefix=prefix if prefix is not None else self.prefix,
            description=description or self.description,
            case_sensitive=self.case_sensitive if case_sensitive is None else case_sensitive,
        )


class LoopTask:
    """
    Background loop helper inspired by Discord bot task loops.
    """

    def __init__(
        self,
        bot: Bot,
        handler: Handler,
        *,
        seconds: float,
        count: int | None = None,
        wait_until_ready: bool = True,
        autostart: bool = True,
    ) -> None:
        if seconds <= 0:
            raise ValueError("seconds must be greater than zero")
        if count is not None and count <= 0:
            raise ValueError("count must be greater than zero when provided")

        self.bot = bot
        self.handler = handler
        self.seconds = seconds
        self.count = count
        self.wait_until_ready = wait_until_ready
        self.autostart = autostart
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._run_count = 0
        self._before_loop_handlers: list[Handler] = []
        self._after_loop_handlers: list[Handler] = []
        self._error_handlers: list[Handler] = []

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def current_loop(self) -> int:
        return self._run_count

    def start(self) -> LoopTask:
        if self.is_running:
            return self

        self._stop_event = threading.Event()
        self.bot.logger.debug(
            "Starting loop task=%s interval=%.2fs count=%s wait_until_ready=%s autostart=%s",
            self.handler.__name__,
            self.seconds,
            self.count if self.count is not None else "infinite",
            self.wait_until_ready,
            self.autostart,
        )
        self._thread = threading.Thread(
            target=self._run_loop,
            name=f"pypufferblow-loop-{self.handler.__name__}",
            daemon=True,
        )
        self._thread.start()
        return self

    def stop(self, *, join_timeout: float = 1.0) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive() and threading.current_thread() is not thread:
            thread.join(timeout=join_timeout)
        if thread is not None and not thread.is_alive():
            self._thread = None
        self.bot.logger.debug("Stopped loop task=%s", self.handler.__name__)

    def restart(self) -> LoopTask:
        self.stop()
        return self.start()

    def before_loop(self) -> Callable[[Handler], Handler]:
        def decorator(handler: Handler) -> Handler:
            self._before_loop_handlers.append(handler)
            return handler

        return decorator

    def after_loop(self) -> Callable[[Handler], Handler]:
        def decorator(handler: Handler) -> Handler:
            self._after_loop_handlers.append(handler)
            return handler

        return decorator

    def on_error(self) -> Callable[[Handler], Handler]:
        def decorator(handler: Handler) -> Handler:
            self._error_handlers.append(handler)
            return handler

        return decorator

    def run_once(self) -> None:
        context = BotContext(bot=self.bot, event_name="loop")
        self.bot.logger.debug(
            "Running loop task=%s iteration=%s",
            self.handler.__name__,
            self._run_count + 1,
        )
        for hook in self._before_loop_handlers:
            self.bot._safe_invoke_handler(hook, context, source_event="loop")

        loop_error: Exception | None = None
        try:
            self.bot._invoke_handler(self.handler, context)
        except Exception as error:
            loop_error = error
            context.error = error
            handled = False
            if self._error_handlers:
                for handler in self._error_handlers:
                    self.bot._safe_invoke_handler(handler, context, source_event="loop")
                handled = True
            if not handled:
                self.bot._handle_handler_error(error, source_event="loop")
        finally:
            self._run_count += 1
            if loop_error is not None:
                context.error = loop_error
            for hook in self._after_loop_handlers:
                self.bot._safe_invoke_handler(hook, context, source_event="loop")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            if self.wait_until_ready and not self.bot._ready_event.wait(timeout=0.1):
                continue

            self.run_once()

            if self.count is not None and self._run_count >= self.count:
                self._stop_event.set()
                break

            if self._stop_event.wait(self.seconds):
                break

        self._thread = None


class BotOptions(ClientOptions):
    """
    High-level options for running decorator-based bots.
    """

    def __init__(
        self,
        *,
        command_prefix: str = "!",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.command_prefix = command_prefix


class BotContext:
    """
    Runtime context passed into bot handlers.
    """

    def __init__(
        self,
        *,
        bot: Bot,
        event_name: str,
        message: WebSocketMessage | None = None,
        error: Exception | None = None,
        reason: str | None = None,
        command_name: str | None = None,
        args: tuple[str, ...] = (),
        lifecycle_event: str | None = None,
    ) -> None:
        self.bot = bot
        self.event_name = event_name
        self.message = message
        self.error = error
        self.reason = reason
        self.command_name = command_name
        self.args = args
        self.lifecycle_event = lifecycle_event

    @property
    def channel_id(self) -> str | None:
        return self.message.channel_id if self.message else None

    @property
    def author_id(self) -> str | None:
        if not self.message:
            return None
        return self.message.sender_user_id or self.message.user_id

    @property
    def author_name(self) -> str | None:
        return self.message.username if self.message else None

    @property
    def content(self) -> str:
        if not self.message:
            return ""
        return self.message.message or self.message.content or ""

    @property
    def command_text(self) -> str:
        return self.content.strip()

    @property
    def users(self):
        return self.bot.get_users_api()

    @property
    def channels(self):
        return self.bot.get_channels_api()

    def reply(self, content: str, attachments: list[str] | None = None) -> None:
        if not self.channel_id:
            raise RuntimeError("Cannot reply without a channel_id on the current context")
        self.bot.send_message(self.channel_id, content, attachments=attachments)

    async def reply_async(
        self,
        content: str,
        attachments: list[str] | None = None,
    ) -> None:
        if not self.channel_id:
            raise RuntimeError("Cannot reply without a channel_id on the current context")
        await self.bot.send_message_async(self.channel_id, content, attachments=attachments)

    def send(
        self,
        channel_id: str,
        content: str,
        attachments: list[str] | None = None,
    ) -> None:
        self.bot.send_message(channel_id, content, attachments=attachments)

    async def send_async(
        self,
        channel_id: str,
        content: str,
        attachments: list[str] | None = None,
    ) -> None:
        await self.bot.send_message_async(channel_id, content, attachments=attachments)

    def mark_as_read(self) -> None:
        if not self.message or not self.channel_id or not self.message.message_id:
            raise RuntimeError("Cannot mark message as read without message and channel context")
        self.bot.mark_message_as_read(self.channel_id, self.message.message_id)

    def mark_read(self) -> None:
        self.mark_as_read()

    async def mark_read_async(self) -> None:
        if not self.message or not self.channel_id or not self.message.message_id:
            raise RuntimeError("Cannot mark message as read without message and channel context")
        await self.bot.mark_message_as_read_async(self.channel_id, self.message.message_id)


class Bot:
    """
    Decorator-based bot application inspired by FastAPI's registration style.
    """

    def __init__(
        self,
        options: BotOptions,
        *,
        client: Client | None = None,
    ) -> None:
        self.options = options
        self.client = client or Client(options)
        self.logger = get_sdk_logger("bot")
        self.websocket = None
        self._running = False
        self._event_handlers: dict[str, list[Handler]] = defaultdict(list)
        self._conditional_event_handlers: list[ConditionalEventRegistration] = []
        self._message_handlers: list[MessageRegistration] = []
        self._commands: list[CommandRegistration] = []
        self._before_command_handlers: list[Handler] = []
        self._after_command_handlers: list[Handler] = []
        self._global_checks: list[Predicate] = []
        self._waiters: dict[str, list[EventWaiter]] = defaultdict(list)
        self._ready = False
        self._ready_event = threading.Event()
        self._ready_waiters: list[tuple[asyncio.Future, asyncio.AbstractEventLoop]] = []
        self._cooldown_states: dict[tuple[int, str], list[float]] = defaultdict(list)
        self._loop_tasks: list[LoopTask] = []

    def on_event(self, event_name: str) -> Callable[[Handler], Handler]:
        normalized_event = event_name.strip().lower()

        def decorator(handler: Handler) -> Handler:
            self._event_handlers[normalized_event].append(handler)
            return handler

        return decorator

    def listen(
        self,
        event_name: str,
        *,
        check: Predicate | None = None,
        once: bool = False,
    ) -> Callable[[Handler], Handler]:
        normalized_event = event_name.strip().lower()

        def decorator(handler: Handler) -> Handler:
            self._conditional_event_handlers.append(
                ConditionalEventRegistration(
                    event_name=normalized_event,
                    handler=handler,
                    check=check,
                    once=once,
                )
            )
            return handler

        return decorator

    def message(
        self,
        *,
        startswith: str | None = None,
        contains: str | None = None,
        channel_id: str | None = None,
        ignore_bots: bool = False,
    ) -> Callable[[Handler], Handler]:
        def decorator(handler: Handler) -> Handler:
            self._message_handlers.append(
                MessageRegistration(
                    handler=handler,
                    startswith=startswith,
                    contains=contains,
                    channel_id=channel_id,
                    ignore_bots=ignore_bots,
                )
            )
            return handler

        return decorator

    def command(
        self,
        name: str | None = None,
        *,
        aliases: Iterable[str] | None = None,
        prefix: str | None = None,
        description: str | None = None,
        usage: str | None = None,
        hidden: bool = False,
        case_sensitive: bool = False,
    ) -> Callable[[Handler], Handler]:
        def decorator(handler: Handler) -> Handler:
            registration = CommandRegistration(
                name=name or handler.__name__,
                handler=handler,
                aliases=tuple(aliases or ()),
                prefix=prefix,
                description=description,
                usage=usage,
                hidden=hidden,
                case_sensitive=case_sensitive,
            )
            self._commands.append(registration)
            return handler

        return decorator

    def get_commands(self, *, include_hidden: bool = False) -> list[CommandRegistration]:
        commands = [registration for registration in self._commands if include_hidden or not registration.hidden]
        return sorted(commands, key=lambda registration: registration.name)

    def get_command(self, name: str) -> CommandRegistration | None:
        normalized_name = name.strip()
        for registration in self._commands:
            if registration.case_sensitive:
                candidate_names = (registration.name, *registration.aliases)
                if normalized_name in candidate_names:
                    return registration
                continue

            lowered_name = normalized_name.lower()
            candidate_names = (registration.name.lower(), *(alias.lower() for alias in registration.aliases))
            if lowered_name in candidate_names:
                return registration
        return None

    def format_help(
        self,
        command_name: str | None = None,
        *,
        include_hidden: bool = False,
    ) -> str:
        if command_name:
            registration = self.get_command(command_name)
            if registration is None or (registration.hidden and not include_hidden):
                raise ValueError(f"Unknown command: {command_name}")
            return self._format_command_help(registration)

        lines = ["Available commands:"]
        for registration in self.get_commands(include_hidden=include_hidden):
            lines.append(self._format_command_summary(registration))
        return "\n".join(lines)

    def install_help_command(
        self,
        *,
        name: str = "help",
        aliases: Iterable[str] | None = None,
        prefix: str | None = None,
        description: str = "Show available bot commands.",
        include_hidden: bool = False,
    ) -> Handler:
        if self.get_command(name) is not None:
            raise ValueError(f"A command named {name!r} is already registered")

        @self.command(
            name,
            aliases=aliases,
            prefix=prefix,
            description=description,
            usage="[command]",
        )
        def _help(ctx: BotContext, *parts: str) -> None:
            target = " ".join(parts).strip() or None
            try:
                help_text = self.format_help(target, include_hidden=include_hidden)
            except ValueError as error:
                ctx.reply(str(error))
                return
            ctx.reply(help_text)

        return _help

    def lifecycle(
        self,
        event_name: str | None = None,
        *,
        check: Predicate | None = None,
        once: bool = False,
    ) -> Callable[[Handler], Handler]:
        normalized_event = event_name.strip().lower() if event_name else None
        if normalized_event is not None and normalized_event not in LIFECYCLE_EVENTS:
            raise ValueError(
                f"Unsupported lifecycle event {event_name!r}. "
                f"Expected one of: {', '.join(sorted(LIFECYCLE_EVENTS))}"
            )

        def lifecycle_check(context: BotContext) -> bool:
            if normalized_event is not None and context.lifecycle_event != normalized_event:
                return False
            if check is None:
                return True
            return self._evaluate_predicate(check, context)

        return self.listen("lifecycle", check=lifecycle_check, once=once)

    def group(
        self,
        name: str,
        *,
        aliases: Iterable[str] | None = None,
        prefix: str | None = None,
        description: str | None = None,
        case_sensitive: bool = False,
    ) -> CommandGroup:
        return CommandGroup(
            self,
            name,
            aliases=aliases,
            prefix=prefix,
            description=description,
            case_sensitive=case_sensitive,
        )

    def startup(self) -> Callable[[Handler], Handler]:
        return self.on_event("startup")

    def shutdown(self) -> Callable[[Handler], Handler]:
        return self.on_event("shutdown")

    def connect(self) -> Callable[[Handler], Handler]:
        return self.on_event("connect")

    def ready(self) -> Callable[[Handler], Handler]:
        return self.on_event("ready")

    def started(self) -> Callable[[Handler], Handler]:
        return self.on_event("started")

    def disconnect(self) -> Callable[[Handler], Handler]:
        return self.on_event("disconnect")

    def error(self) -> Callable[[Handler], Handler]:
        return self.on_event("error")

    def stopped(self) -> Callable[[Handler], Handler]:
        return self.on_event("stopped")

    def event(self, event_name: str) -> Callable[[Handler], Handler]:
        return self.on_event(event_name)

    def when(
        self,
        event_name: str,
        *,
        check: Predicate | None = None,
    ) -> Callable[[Handler], Handler]:
        return self.listen(event_name, check=check)

    def once(
        self,
        event_name: str,
        *,
        check: Predicate | None = None,
    ) -> Callable[[Handler], Handler]:
        return self.listen(event_name, check=check, once=True)

    def on_message(
        self,
        *,
        startswith: str | None = None,
        contains: str | None = None,
        channel_id: str | None = None,
        ignore_bots: bool = False,
    ) -> Callable[[Handler], Handler]:
        return self.message(
            startswith=startswith,
            contains=contains,
            channel_id=channel_id,
            ignore_bots=ignore_bots,
        )

    def before_command(self) -> Callable[[Handler], Handler]:
        def decorator(handler: Handler) -> Handler:
            self._before_command_handlers.append(handler)
            return handler

        return decorator

    def after_command(self) -> Callable[[Handler], Handler]:
        def decorator(handler: Handler) -> Handler:
            self._after_command_handlers.append(handler)
            return handler

        return decorator

    def add_check(self, predicate: Predicate) -> Predicate:
        self._global_checks.append(predicate)
        return predicate

    def check(self, predicate: Predicate) -> Callable[[Handler], Handler]:
        def decorator(handler: Handler) -> Handler:
            attached_checks = list(getattr(handler, "__bot_checks__", ()))
            attached_checks.append(predicate)
            setattr(handler, "__bot_checks__", tuple(attached_checks))
            return handler

        return decorator

    def cooldown(
        self,
        rate: int,
        per: float,
        *,
        bucket: str = "user",
    ) -> Callable[[Handler], Handler]:
        if rate <= 0:
            raise ValueError("rate must be greater than zero")
        if per <= 0:
            raise ValueError("per must be greater than zero")
        if bucket not in {"user", "channel", "global"}:
            raise ValueError("bucket must be one of: user, channel, global")

        def decorator(handler: Handler) -> Handler:
            setattr(handler, "__bot_cooldown__", (rate, per, bucket))
            return handler

        return decorator

    def loop(
        self,
        *,
        seconds: float,
        count: int | None = None,
        wait_until_ready: bool = True,
        autostart: bool = True,
    ) -> Callable[[Handler], LoopTask]:
        def decorator(handler: Handler) -> LoopTask:
            loop_task = LoopTask(
                self,
                handler,
                seconds=seconds,
                count=count,
                wait_until_ready=wait_until_ready,
                autostart=autostart,
            )
            self._loop_tasks.append(loop_task)
            return loop_task

        return decorator

    def get_users_api(self):
        users_api = getattr(self.client, "users", None)
        return users_api() if callable(users_api) else users_api

    def get_channels_api(self):
        channels_api = getattr(self.client, "channels", None)
        return channels_api() if callable(channels_api) else channels_api

    def get_global_websocket(self):
        websocket_api = getattr(self.client, "websocket", None)
        return websocket_api() if callable(websocket_api) else websocket_api

    def get_channel_websocket(self, channel_id: str):
        factory = getattr(self.client, "create_channel_websocket", None)
        if factory is None:
            raise RuntimeError("Client does not support channel-specific websockets")
        return factory(channel_id)

    def authenticate(self, *, sign_up: bool = False) -> str:
        users_api = self.get_users_api()
        if users_api is None:
            raise RuntimeError("Client does not expose a users API")

        if getattr(users_api, "is_signed_in", False) and getattr(users_api.user, "auth_token", None):
            self.logger.debug(
                "Reusing existing authentication for %s on %s",
                self.options.username,
                self.options.instance_url,
            )
            return users_api.user.auth_token

        self.logger.info(
            "Authenticating bot user=%s against home instance=%s using %s",
            self.options.username,
            self.options.instance_url,
            "sign_up" if sign_up else "sign_in",
        )
        if sign_up:
            users_api.sign_up()
        else:
            users_api.sign_in()

        channels_api = self.get_channels_api()
        if channels_api is None:
            raise RuntimeError("Client does not expose a channels API after authentication")

        return users_api.user.auth_token

    async def authenticate_async(self, *, sign_up: bool = False) -> str:
        return await asyncio.to_thread(self.authenticate, sign_up=sign_up)

    def start(
        self,
        *,
        channel_id: str | None = None,
        sign_up: bool = False,
    ) -> Bot:
        self.logger.info(
            "Starting bot user=%s instance=%s channel_scope=%s",
            self.options.username,
            self.options.instance_url,
            channel_id or "global",
        )
        self.authenticate(sign_up=sign_up)
        self._running = True
        self._dispatch_lifecycle_event("startup")

        self.websocket = (
            self.get_channel_websocket(channel_id)
            if channel_id
            else self.get_global_websocket()
        )
        if self.websocket is None:
            raise RuntimeError("Client did not return a websocket instance")

        self.websocket.on_connected = self._on_websocket_connected
        self.websocket.on_disconnected = (
            lambda reason: self._on_websocket_disconnected(reason)
        )
        self.websocket.on_error = (
            lambda error: self._dispatch_lifecycle_event("error", error=error)
        )
        self.websocket.on_message = self.process_websocket_message
        self.websocket.connect()
        self._start_autoloops()
        self._dispatch_lifecycle_event("started")
        return self

    async def start_async(
        self,
        *,
        channel_id: str | None = None,
        sign_up: bool = False,
    ) -> Bot:
        return await asyncio.to_thread(self.start, channel_id=channel_id, sign_up=sign_up)

    def run(
        self,
        *,
        channel_id: str | None = None,
        sign_up: bool = False,
        poll_interval: float = 0.25,
    ) -> None:
        self.start(channel_id=channel_id, sign_up=sign_up)
        try:
            while self._running:
                time.sleep(poll_interval)
        except KeyboardInterrupt:
            self.stop()
            raise

    async def run_async(
        self,
        *,
        channel_id: str | None = None,
        sign_up: bool = False,
        poll_interval: float = 0.25,
    ) -> None:
        await self.start_async(channel_id=channel_id, sign_up=sign_up)
        try:
            while self._running:
                await asyncio.sleep(poll_interval)
        finally:
            if self._running:
                await self.stop_async()

    def stop(self) -> None:
        self.logger.info("Stopping bot user=%s", self.options.username)
        self._running = False
        self._ready = False
        self._ready_event.clear()
        self._stop_loop_tasks()
        if self.websocket is not None:
            self.websocket.disconnect()
            self.websocket = None
        self._dispatch_lifecycle_event("shutdown")
        self._dispatch_lifecycle_event("stopped")

    async def stop_async(self) -> None:
        await asyncio.to_thread(self.stop)

    def __enter__(self) -> Bot:
        return self.start()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()

    async def __aenter__(self) -> Bot:
        return await self.start_async()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.stop_async()

    def process_websocket_message(self, message: WebSocketMessage) -> None:
        event_name = (message.type or "message").lower()
        self.logger.debug(
            "Received websocket event=%s channel_id=%s author=%s",
            event_name,
            message.channel_id,
            message.username,
        )
        context = BotContext(bot=self, event_name=event_name, message=message)

        self._dispatch_event(event_name, context)

        if event_name == "message":
            self._dispatch_message_handlers(context)
            self._dispatch_command_handlers(context)

    async def wait_for(
        self,
        event_name: str,
        *,
        check: Predicate | None = None,
        timeout: float | None = None,
    ) -> BotContext:
        normalized_event = event_name.strip().lower()
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self._waiters[normalized_event].append(
            EventWaiter(
                event_name=normalized_event,
                future=future,
                loop=loop,
                check=check,
            )
        )
        return await asyncio.wait_for(future, timeout=timeout)

    async def wait_until_ready(self, timeout: float | None = None) -> None:
        if self._ready:
            return

        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self._ready_waiters.append((future, loop))
        await asyncio.wait_for(future, timeout=timeout)

    async def wait_for_lifecycle(
        self,
        event_name: str,
        *,
        timeout: float | None = None,
    ) -> BotContext:
        normalized_event = event_name.strip().lower()
        if normalized_event not in LIFECYCLE_EVENTS:
            raise ValueError(
                f"Unsupported lifecycle event {event_name!r}. "
                f"Expected one of: {', '.join(sorted(LIFECYCLE_EVENTS))}"
            )
        return await self.wait_for(
            "lifecycle",
            check=lambda ctx: ctx.lifecycle_event == normalized_event,
            timeout=timeout,
        )

    def send_message(
        self,
        channel_id: str,
        content: str,
        *,
        attachments: list[str] | None = None,
    ) -> None:
        channels_api = self.get_channels_api()
        if channels_api is None:
            raise RuntimeError("Client does not expose a channels API")
        channels_api.send_message(channel_id=channel_id, message=content, attachments=attachments)

    async def send_message_async(
        self,
        channel_id: str,
        content: str,
        *,
        attachments: list[str] | None = None,
    ) -> None:
        await asyncio.to_thread(
            self.send_message,
            channel_id,
            content,
            attachments=attachments,
        )

    def mark_message_as_read(self, channel_id: str, message_id: str) -> None:
        channels_api = self.get_channels_api()
        if channels_api is None:
            raise RuntimeError("Client does not expose a channels API")
        channels_api.mark_message_as_read(channel_id=channel_id, message_id=message_id)

    async def mark_message_as_read_async(self, channel_id: str, message_id: str) -> None:
        await asyncio.to_thread(self.mark_message_as_read, channel_id, message_id)

    def _dispatch_lifecycle_event(
        self,
        event_name: str,
        *,
        error: Exception | None = None,
        reason: str | None = None,
    ) -> None:
        context = BotContext(
            bot=self,
            event_name=event_name,
            error=error,
            reason=reason,
            lifecycle_event=event_name,
        )
        self._dispatch_event(event_name, context)
        lifecycle_context = BotContext(
            bot=self,
            event_name="lifecycle",
            error=error,
            reason=reason,
            lifecycle_event=event_name,
        )
        self._dispatch_event("lifecycle", lifecycle_context)

    def _dispatch_event(self, event_name: str, context: BotContext) -> None:
        self._resolve_waiters(event_name, context)
        for handler in self._event_handlers.get(event_name, []):
            self._safe_invoke_handler(handler, context, source_event=event_name)
        remaining_handlers: list[ConditionalEventRegistration] = []
        for registration in self._conditional_event_handlers:
            if registration.event_name != event_name:
                remaining_handlers.append(registration)
                continue
            if registration.check is not None and not self._evaluate_predicate(registration.check, context):
                remaining_handlers.append(registration)
                continue
            self._safe_invoke_handler(registration.handler, context, source_event=event_name)
            if not registration.once:
                remaining_handlers.append(registration)
        self._conditional_event_handlers = remaining_handlers

    def _dispatch_message_handlers(self, context: BotContext) -> None:
        for registration in self._message_handlers:
            if registration.channel_id and registration.channel_id != context.channel_id:
                continue
            if registration.ignore_bots and context.author_name == self.options.username:
                continue
            if registration.startswith and not context.content.startswith(registration.startswith):
                continue
            if registration.contains and registration.contains not in context.content:
                continue
            self._safe_invoke_handler(registration.handler, context, source_event="message")

    def _dispatch_command_handlers(self, context: BotContext) -> None:
        content = context.content.strip()
        if not content:
            return

        best_match: tuple[CommandRegistration, list[str], int] | None = None

        for registration in self._commands:
            prefix = registration.prefix or self.options.command_prefix
            if not content.startswith(prefix):
                continue

            command_body = content[len(prefix):].strip()
            if not command_body:
                return

            try:
                parts = shlex.split(command_body)
            except ValueError as error:
                self._handle_handler_error(error, source_event="command")
                return
            if not parts:
                return

            matched_tokens = self._match_command_tokens(
                parts,
                (registration.name, *registration.aliases),
                registration.case_sensitive,
            )
            if matched_tokens == 0:
                continue
            if best_match is None or matched_tokens > best_match[2]:
                best_match = (registration, parts, matched_tokens)

        if best_match is None:
            return

        registration, parts, matched_tokens = best_match
        self.logger.debug(
            "Matched command name=%s author=%s channel_id=%s args=%s",
            registration.name,
            context.author_name,
            context.channel_id,
            parts[matched_tokens:],
        )
        command_context = BotContext(
            bot=self,
            event_name="command",
            message=context.message,
            command_name=registration.name,
            args=tuple(parts[matched_tokens:]),
        )

        try:
            self._apply_cooldown(registration, command_context)
            self._run_command_checks(registration.handler, command_context)
        except Exception as error:
            self._handle_handler_error(error, source_event="command")
            return

        try:
            bound_args = self._build_command_arguments(
                registration.handler,
                command_context,
                list(parts[matched_tokens:]),
            )
        except Exception as error:
            self._handle_handler_error(error, source_event="command")
            return

        self._dispatch_event("command", command_context)

        command_error: Exception | None = None
        for hook in self._before_command_handlers:
            try:
                self._invoke_handler(hook, command_context)
            except Exception as error:
                command_error = error
                self._handle_handler_error(error, source_event="command")
                break

        if command_error is None:
            try:
                self._invoke_handler(registration.handler, *bound_args)
            except Exception as error:
                command_error = error
                self._handle_handler_error(error, source_event="command")

        if command_error is not None:
            command_context.error = command_error

        for hook in self._after_command_handlers:
            self._safe_invoke_handler(hook, command_context, source_event="command")

    def _format_command_summary(self, registration: CommandRegistration) -> str:
        prefix = registration.prefix or self.options.command_prefix
        usage_suffix = f" {registration.usage}" if registration.usage else ""
        description_suffix = f" - {registration.description}" if registration.description else ""
        return f"{prefix}{registration.name}{usage_suffix}{description_suffix}"

    def _format_command_help(self, registration: CommandRegistration) -> str:
        prefix = registration.prefix or self.options.command_prefix
        lines = [f"Command: {prefix}{registration.name}"]
        if registration.description:
            lines.append(f"Description: {registration.description}")
        if registration.usage:
            lines.append(f"Usage: {prefix}{registration.name} {registration.usage}")
        if registration.aliases:
            lines.append(f"Aliases: {', '.join(f'{prefix}{alias}' for alias in registration.aliases)}")
        return "\n".join(lines)

    @staticmethod
    def _matches_command(
        incoming_name: str,
        candidate_names: tuple[str, ...],
        case_sensitive: bool,
    ) -> bool:
        if case_sensitive:
            return incoming_name in candidate_names
        lowered = incoming_name.lower()
        return any(candidate.lower() == lowered for candidate in candidate_names)

    @classmethod
    def _match_command_tokens(
        cls,
        incoming_tokens: list[str],
        candidate_names: tuple[str, ...],
        case_sensitive: bool,
    ) -> int:
        best_match = 0
        for candidate in candidate_names:
            candidate_tokens = candidate.split()
            if len(candidate_tokens) > len(incoming_tokens):
                continue
            if cls._tokens_match(
                incoming_tokens[: len(candidate_tokens)],
                candidate_tokens,
                case_sensitive,
            ):
                best_match = max(best_match, len(candidate_tokens))
        return best_match

    @staticmethod
    def _tokens_match(
        incoming_tokens: list[str],
        candidate_tokens: list[str],
        case_sensitive: bool,
    ) -> bool:
        if case_sensitive:
            return incoming_tokens == candidate_tokens
        return [token.lower() for token in incoming_tokens] == [
            token.lower() for token in candidate_tokens
        ]

    def _build_command_arguments(
        self,
        handler: Handler,
        context: BotContext,
        tokens: list[str],
    ) -> list[Any]:
        signature = inspect.signature(handler)
        type_hints = get_type_hints(handler)
        parameters = list(signature.parameters.values())
        if not parameters:
            if tokens:
                raise ValueError("Command handler does not accept arguments")
            return []

        bound_arguments: list[Any] = [context]
        token_index = 0

        for parameter in parameters[1:]:
            annotation = type_hints.get(parameter.name, parameter.annotation)
            if parameter.kind is inspect.Parameter.VAR_POSITIONAL:
                remaining_tokens = tokens[token_index:]
                if annotation in (inspect._empty, str):
                    bound_arguments.extend(remaining_tokens)
                else:
                    bound_arguments.extend(
                        self._convert_argument(token, annotation) for token in remaining_tokens
                    )
                token_index = len(tokens)
                continue

            if token_index < len(tokens):
                bound_arguments.append(
                    self._convert_argument(tokens[token_index], annotation)
                )
                token_index += 1
                continue

            if parameter.default is inspect._empty:
                raise ValueError(f"Missing required command argument: {parameter.name}")

            bound_arguments.append(parameter.default)

        if token_index < len(tokens):
            raise ValueError("Too many command arguments provided")

        return bound_arguments

    @staticmethod
    def _convert_argument(raw_value: str, annotation: Any) -> Any:
        origin = get_origin(annotation)
        if origin in (UnionType, Union):
            union_args = tuple(arg for arg in get_args(annotation) if arg is not type(None))
            if union_args:
                last_error: Exception | None = None
                for candidate in union_args:
                    try:
                        return Bot._convert_argument(raw_value, candidate)
                    except Exception as error:  # pragma: no cover - exercised through fallback
                        last_error = error
                if last_error is not None:
                    raise last_error

        if annotation is inspect._empty or annotation is str:
            return raw_value
        if annotation is int:
            return int(raw_value)
        if annotation is float:
            return float(raw_value)
        if annotation is bool:
            lowered = raw_value.lower()
            if lowered in {"1", "true", "yes", "on"}:
                return True
            if lowered in {"0", "false", "no", "off"}:
                return False
            raise ValueError(f"Cannot parse boolean value from {raw_value!r}")
        return raw_value

    def _safe_invoke_handler(
        self,
        handler: Handler,
        *args: Any,
        source_event: str,
    ) -> None:
        try:
            self._invoke_handler(handler, *args)
        except Exception as error:
            self._handle_handler_error(error, source_event=source_event)

    def _run_command_checks(self, handler: Handler, context: BotContext) -> None:
        checks = [*self._global_checks, *getattr(handler, "__bot_checks__", ())]
        for predicate in checks:
            if not self._evaluate_predicate(predicate, context):
                raise BotCheckFailure(
                    f"Command check failed for {context.command_name or handler.__name__}"
                )

    def _apply_cooldown(self, registration: CommandRegistration, context: BotContext) -> None:
        cooldown = registration.cooldown or getattr(registration.handler, "__bot_cooldown__", None)
        if cooldown is None:
            return

        rate, per, bucket = cooldown
        bucket_key = self._resolve_cooldown_bucket(bucket, context)
        state_key = (id(registration.handler), bucket_key)
        timestamps = self._cooldown_states[state_key]
        now = time.monotonic()
        valid_after = now - per
        timestamps[:] = [timestamp for timestamp in timestamps if timestamp > valid_after]

        if len(timestamps) >= rate:
            retry_after = max(0.0, per - (now - timestamps[0]))
            self.logger.debug(
                "Command %s is on cooldown bucket=%s retry_after=%.2fs",
                context.command_name,
                state_key[1],
                retry_after,
            )
            raise CommandOnCooldown(retry_after)

        timestamps.append(now)

    def reset_command_cooldown(
        self,
        command: str | Handler,
        *,
        context: BotContext | None = None,
        bucket_key: str | None = None,
    ) -> int:
        registrations = self._resolve_command_registrations(command)
        if not registrations:
            raise ValueError(f"Unknown command: {command!r}")

        removed = 0
        if context is None and bucket_key is None:
            handler_ids = {id(registration.handler) for registration in registrations}
            for state_key in list(self._cooldown_states):
                if state_key[0] in handler_ids:
                    self._cooldown_states.pop(state_key, None)
                    removed += 1
            self.logger.info("Reset %s cooldown bucket(s) for command=%r", removed, command)
            return removed

        for registration in registrations:
            cooldown = registration.cooldown or getattr(registration.handler, "__bot_cooldown__", None)
            if cooldown is None:
                continue
            _, _, bucket = cooldown
            resolved_bucket_key = bucket_key or self._resolve_cooldown_bucket(
                bucket,
                context or BotContext(bot=self, event_name="command"),
            )
            state_key = (id(registration.handler), resolved_bucket_key)
            if state_key in self._cooldown_states:
                self._cooldown_states.pop(state_key, None)
                removed += 1
        self.logger.info(
            "Reset %s cooldown bucket(s) for command=%r bucket=%s",
            removed,
            command,
            bucket_key or "derived",
        )
        return removed

    @staticmethod
    def _resolve_cooldown_bucket(bucket: str, context: BotContext) -> str:
        if bucket == "global":
            return "global"
        if bucket == "channel":
            return context.channel_id or "unknown-channel"
        return context.author_id or context.author_name or "unknown-user"

    @staticmethod
    def _set_future_result(future: asyncio.Future, value: Any) -> None:
        if not future.done():
            future.set_result(value)

    @staticmethod
    def _set_future_exception(future: asyncio.Future, error: Exception) -> None:
        if not future.done():
            future.set_exception(error)

    def _resolve_waiters(self, event_name: str, context: BotContext) -> None:
        waiters = self._waiters.get(event_name)
        if not waiters:
            return

        remaining_waiters: list[EventWaiter] = []
        for waiter in waiters:
            if waiter.future.cancelled() or waiter.future.done():
                continue
            try:
                matched = True if waiter.check is None else self._evaluate_predicate(waiter.check, context)
            except Exception as error:
                waiter.loop.call_soon_threadsafe(self._set_future_exception, waiter.future, error)
                continue

            if matched:
                waiter.loop.call_soon_threadsafe(self._set_future_result, waiter.future, context)
            else:
                remaining_waiters.append(waiter)

        if remaining_waiters:
            self._waiters[event_name] = remaining_waiters
        else:
            self._waiters.pop(event_name, None)

    def _resolve_ready_waiters(self) -> None:
        pending_waiters = self._ready_waiters
        self._ready_waiters = []
        for future, loop in pending_waiters:
            if future.cancelled() or future.done():
                continue
            loop.call_soon_threadsafe(self._set_future_result, future, None)

    def _on_websocket_connected(self) -> None:
        self._ready = True
        self._ready_event.set()
        self.logger.info("Websocket connected; bot is ready on %s", self.options.instance_url)
        self._dispatch_lifecycle_event("connect")
        self._dispatch_lifecycle_event("ready")
        self._resolve_ready_waiters()

    def _on_websocket_disconnected(self, reason: str) -> None:
        self._ready = False
        self._ready_event.clear()
        self.logger.info("Websocket disconnected reason=%s", reason)
        self._dispatch_lifecycle_event("disconnect", reason=reason)

    @staticmethod
    def _evaluate_predicate(predicate: Predicate, context: BotContext) -> bool:
        result = predicate(context)
        if inspect.isawaitable(result):
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                return bool(asyncio.run(result))
            raise RuntimeError(
                "Async predicates are not supported from an active event loop; use a synchronous predicate."
            )
        return bool(result)

    def _handle_handler_error(self, error: Exception, *, source_event: str) -> None:
        self.logger.error(
            "Handler error source_event=%s error=%s",
            source_event,
            error,
        )
        if source_event == "error":
            raise error

        if not self._event_handlers.get("error"):
            raise error

        self._dispatch_lifecycle_event("error", error=error)

    def _invoke_handler(self, handler: Handler, *args: Any) -> None:
        result = handler(*args)
        if inspect.isawaitable(result):
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(result)
            else:
                loop.create_task(result)

    def _start_autoloops(self) -> None:
        for loop_task in self._loop_tasks:
            if loop_task.autostart:
                self.logger.debug("Autostarting loop task=%s", loop_task.handler.__name__)
                loop_task.start()

    def _stop_loop_tasks(self) -> None:
        for loop_task in self._loop_tasks:
            loop_task.stop()

    def _resolve_command_registrations(
        self,
        command: str | Handler,
    ) -> list[CommandRegistration]:
        if callable(command):
            return [registration for registration in self._commands if registration.handler is command]

        normalized_name = command.strip()
        matches: list[CommandRegistration] = []
        for registration in self._commands:
            if registration.case_sensitive:
                names = {registration.name, *registration.aliases}
                if normalized_name in names:
                    matches.append(registration)
                continue

            lowered_name = normalized_name.lower()
            candidate_names = {registration.name.lower(), *(alias.lower() for alias in registration.aliases)}
            if lowered_name in candidate_names:
                matches.append(registration)
        return matches
