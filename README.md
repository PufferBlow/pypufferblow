# pypufferblow
The official SDK for pufferblow

## Installation

```bash
pip install pypufferblow
# or via Poetry
poetry add pypufferblow
```

## Quick Start

```python
from pypufferblow import Client, ClientOptions

# Initialize client against your home instance
client_options = ClientOptions(
    instance="https://chat.example.org",
    username="your_username",
    password="your_password"
)
client = Client(client_options)

# Authenticate
client.users.sign_in()
# or client.users.sign_up() for new users

# Use channels
channels = client.channels()
channel_list = channels.list_channels()

# Send a message
channels.send_message(channel_id="some_channel_id", message="Hello!")

# Send a message with attachments
channels.send_message(
    channel_id="some_channel_id",
    message="Check this out!",
    attachments=["path/to/image.png", "path/to/document.pdf"]
)

# Real-time messaging with WebSocket
ws = client.websocket()
def on_message(msg):
    print(f"Received: {msg.message}")
    if msg.attachments:
        print("Attachments:", msg.attachments)
ws.on_message = on_message
ws.connect()

# For specific channels only
ws_channel = client.create_channel_websocket(channel_id="some_channel_id")
ws_channel.connect()
```

## Bot SDK

`pypufferblow` includes a decorator-style bot SDK designed for building bots against a Pufferblow home instance. It keeps the existing low-level `Client` API available, but the recommended entrypoint for bots is `Bot`.

```python
from pypufferblow import Bot, BotOptions

bot = Bot(
    BotOptions(
        instance="https://chat.example.org",
        username="my_bot",
        password="super-secret",
        command_prefix="!",
    )
)

@bot.startup()
def startup(ctx):
    print("bot connected")

@bot.connect()
def connected(ctx):
    print("websocket connected")

@bot.started()
def started(ctx):
    print("bot is fully started")

@bot.shutdown()
def shutdown(ctx):
    print("bot is shutting down")

@bot.message(startswith="!")
def observe_commands(ctx):
    print("incoming command:", ctx.content)

@bot.command("ping")
def ping(ctx):
    ctx.reply("pong")

@bot.command("sum")
def sum_numbers(ctx, left: int, right: int):
    ctx.reply(str(left + right))

@bot.error()
def on_error(ctx):
    print("bot error:", ctx.error)

bot.run()
```

Readable verbose logging is available when you want to trace lifecycle,
websocket, command, and loop activity during development:

```python
from pypufferblow import Bot, BotOptions

bot = Bot(
    BotOptions(
        instance="https://chat.example.org",
        username="my_bot",
        password="super-secret",
        verbose=True,
    )
)
```

That enables human-readable SDK logs like:

```text
14:02:11 | INFO    | bot | Starting bot user=my_bot instance=https://chat.example.org channel_scope=global
14:02:11 | INFO    | bot | Websocket connected; bot is ready on https://chat.example.org
14:02:15 | DEBUG   | bot | Matched command name=ping author=alice channel_id=general args=[]
```

The same readable logger is also used by the low-level SDK APIs, so verbose mode
helps with:

- user sign-in and sign-up
- profile and user listing
- channel listing and channel info lookups
- message loading and send/read flows
- federated follows and direct messages through your home instance

### Bot Decorators

- `@bot.on_event("startup" | "shutdown" | "connect" | "disconnect" | "error" | "message" | ...)`
- `@bot.startup()`
- `@bot.shutdown()`
- `@bot.connect()`
- `@bot.started()`
- `@bot.disconnect()`
- `@bot.stopped()`
- `@bot.error()`
- `@bot.lifecycle(event_name=None, check=...)`
- `@bot.listen(event_name, check=...)`
- `@bot.when(event_name, check=...)`
- `@bot.once(event_name, check=...)`
- `@bot.message(startswith=..., contains=..., channel_id=...)`
- `@bot.command(name, aliases=..., prefix=...)`
- `bot.group(name, aliases=...)`
- `bot.get_commands()`
- `bot.get_command(name)`
- `bot.format_help(command_name=None)`
- `bot.install_help_command()`
- `@bot.before_command()`
- `@bot.after_command()`
- `@bot.check(predicate)`
- `@bot.cooldown(rate, per, bucket="user" | "channel" | "global")`
- `@bot.loop(seconds=..., count=..., wait_until_ready=True, autostart=True)`

### Bot Context

Handlers receive a `BotContext` object with convenience helpers:

- `ctx.content`
- `ctx.command_text`
- `ctx.author_id`
- `ctx.author_name`
- `ctx.channel_id`
- `ctx.users`
- `ctx.channels`
- `ctx.reply("hello")`
- `await ctx.reply_async("hello")`
- `ctx.send(channel_id, "hello")`
- `await ctx.send_async(channel_id, "hello")`
- `ctx.mark_as_read()`
- `await ctx.mark_read_async()`

### Home Instance Addressing

The preferred way to configure the SDK is with an `instance` URL:

```python
ClientOptions(
    instance="https://chat.example.org",
    username="bot",
    password="secret",
)
```

`host` and `port` still work for compatibility and local development:

```python
ClientOptions(
    host="localhost",
    port=7575,
    username="bot",
    password="secret",
)
```

For federated deployments, keep one home instance as the authenticated API
authority and use the `Federation` API for remote ActivityPub handles and
cross-instance DMs.

Some backend-facing methods and payload fields still use `server_*` naming for
compatibility with the current Pufferblow API. The SDK now also exposes
instance-oriented aliases where that improves bot/client ergonomics.

### Typed Commands

Command handlers support simple FastAPI-style typed parameters after `ctx`:

```python
@bot.command("ban")
def ban_user(ctx, user_id: str, delete_days: int = 0, notify: bool = True):
    ctx.reply(
        f"user={user_id} delete_days={delete_days} notify={notify}"
    )
```

Supported conversions:

- `str`
- `int`
- `float`
- `bool`
- optional unions such as `str | None`

Varargs are also supported:

```python
@bot.command("say")
def say(ctx, *parts: str):
    ctx.reply(" ".join(parts))
```

### Async Bot Operations

The bot layer now includes async helpers for integration with existing event
loops:

```python
await bot.authenticate_async()
await bot.start_async()
await bot.send_message_async("general", "hello")
await bot.mark_message_as_read_async("general", "msg-1")
await bot.stop_async()
```

The low-level APIs also expose async wrappers for common operations:

```python
auth_token = await client.users.sign_in_async()
channels = await client.channels.list_channels_async()
messages = await client.channels.load_messages_async("general")
```

### Waiting For Events

Discord-style conditional waiting is available with `wait_for(...)`:

```python
message_ctx = await bot.wait_for(
    "message",
    check=lambda ctx: ctx.author_name == "alice" and ctx.content == "!ready",
    timeout=30,
)
await message_ctx.reply_async("ready acknowledged")

await bot.wait_until_ready()
```

Lifecycle-specific waiting is also available:

```python
await bot.wait_for_lifecycle("started")
await bot.wait_for_lifecycle("shutdown")
```

### Lifecycle Events

The bot runtime now exposes a fuller lifecycle model:

- `startup`: bot start requested and authentication/bootstrap is beginning
- `connect`: websocket connected
- `ready`: websocket ready for live events
- `started`: bot startup flow is complete
- `disconnect`: websocket disconnected
- `shutdown`: shutdown flow started
- `stopped`: bot shutdown is complete
- `error`: lifecycle or handler error event

Use `@bot.lifecycle()` to observe all lifecycle transitions, or
`@bot.lifecycle("shutdown")` to react to one specific lifecycle phase.

### Command Hooks And Checks

Use hooks and checks to build richer bot workflows:

```python
@bot.before_command()
def before_command(ctx):
    print("running", ctx.command_name)

@bot.after_command()
def after_command(ctx):
    print("finished", ctx.command_name, "error=", ctx.error)

@bot.check(lambda ctx: ctx.author_name != "blocked-user")
@bot.command("ping")
def ping(ctx):
    ctx.reply("pong")
```

Cooldowns are also available:

```python
@bot.cooldown(1, 30, bucket="user")
@bot.command("quote")
def quote(ctx):
    ctx.reply("one quote every 30 seconds per user")
```

Cooldown state can also be cleared deliberately:

```python
bot.reset_command_cooldown("quote", bucket_key="user-123")
```

### Command Groups

Grouped commands behave much closer to Discord bot SDKs:

```python
admin = bot.group("admin", aliases=("mod",))

@admin.command("ban")
def ban(ctx, user_id: str):
    ctx.reply(f"banned {user_id}")

@admin.command("announce")
def announce(ctx, *parts: str):
    ctx.reply(" ".join(parts))
```

This lets your bot respond to commands like `!admin ban user-1` and
`!mod announce maintenance starts now`.

### Command Help And Introspection

Bots can inspect registered commands and expose a built-in help command:

```python
@bot.command("ping", description="Health check", usage="[target]")
def ping(ctx):
    ctx.reply("pong")

bot.install_help_command()

print(bot.format_help())
print(bot.format_help("ping"))
```

You can also inspect command registrations directly:

```python
for command in bot.get_commands():
    print(command.name, command.description)

registration = bot.get_command("ping")
```

Hidden commands are supported too:

```python
@bot.command("owner-sync", hidden=True)
def owner_sync(ctx):
    ...
```

### Background Loop Tasks

Bots can also run scheduled background tasks:

```python
@bot.loop(seconds=60, wait_until_ready=True)
def heartbeat(ctx):
    print("bot is alive on", ctx.bot.options.instance_url)
```

Loop tasks return a `LoopTask` object, so you can start and stop them manually
when you need more control:

```python
@bot.loop(seconds=5, autostart=False, wait_until_ready=False)
def poll_remote_inbox(ctx):
    print("polling...")

poll_remote_inbox.start()
poll_remote_inbox.stop()
```

Loop tasks also support lifecycle hooks:

```python
@bot.loop(seconds=30, wait_until_ready=False)
def sync_remote_state(ctx):
    print("syncing...")

@sync_remote_state.before_loop()
def before_sync(ctx):
    print("about to sync")

@sync_remote_state.after_loop()
def after_sync(ctx):
    print("sync finished", ctx.error)

@sync_remote_state.on_error()
def on_sync_error(ctx):
    print("sync failed:", ctx.error)
```

### Context Managers

Bots can be managed with context managers too:

```python
with bot:
    ...
```

And in async applications:

```python
async with bot:
    await bot.wait_until_ready()
    ...
```

## Features

### User Management
- Sign up new users
- Sign in existing users
- Update user profiles (username, status, password)
- Reset authentication tokens
- List all users

### Channel Management
- Create channels (admin/owner only)
- List accessible channels
- Delete channels (admin/owner only)
- Add/remove users from channels (admin/owner only)
- Send messages to channels
- Load message history
- Mark messages as read
- Delete messages

### Real-time Messaging
- Global WebSocket for all accessible channels
- Channel-specific WebSockets
- Automatic reconnection
- Message callbacks
- Send read confirmations

### Federation and Cross-Instance DMs
- Follow remote ActivityPub accounts (`user@domain`)
- Send direct messages to local users and remote federated users
- Load DM history using unified conversation IDs
- Treat the authenticated home instance as the API authority for those actions

## API Reference

### Client

Main client class that provides access to all SDK features.

```python
client = Client(
    ClientOptions(
        instance="https://chat.example.org",
        username="user",
        password="pass",
    )
)
```

### Users

Handle user authentication and profiles.

```python
users = client.users()
users.sign_in()
users.update_username("new_username")
```

### Channels

Manage channels and messaging.

```python
channels = client.channels()
channels.send_message(channel_id, "Hello!")
channels.send_message(channel_id, "Hello!", attachments=["image.png", "doc.pdf"])
messages = channels.load_messages(channel_id)
```

### WebSocket

Real-time message receiving.

```python
ws = client.websocket()
ws.on_message = lambda msg: print(msg.message)
ws.connect()
```

### System

Inspect and update home-instance information and operational state.

```python
system = client.system()
instance_info = system.get_instance_info()
instance_stats = system.get_instance_stats()
```

### Federation

Follow remote accounts and exchange DMs across instances through your home
instance.

```python
federation = client.federation()

# Follow a remote ActivityPub account
federation.follow_remote_account("alice@example.org")

# Send DM to local user by user_id or username
federation.send_direct_message(peer="local_username", message="hey")

# Send DM to remote handle
federation.send_direct_message(peer="alice@example.org", message="hello from pufferblow")

# Load DM conversation
dm_data = federation.load_direct_messages(peer="alice@example.org", page=1, messages_per_page=20)
```

## Requirements

- Python >= 3.11
- requests
- websockets
- pydantic (for data validation)

## License

GNU 3.0
