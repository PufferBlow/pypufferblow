<div align="center">

<img src="https://raw.githubusercontent.com/PufferBlow/client/main/public/pufferblow-logo.svg" width="120" alt="Pufferblow logo" />

# pypufferblow

**The official Python SDK and bot framework for Pufferblow.**

[![License: GPL-3.0](https://img.shields.io/badge/license-GPL--3.0-blue?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![PyPI](https://img.shields.io/pypi/v/pypufferblow?style=flat-square&color=blue)](https://pypi.org/project/pypufferblow/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/pypufferblow?style=flat-square)](https://pypi.org/project/pypufferblow/)
[![CI](https://img.shields.io/github/actions/workflow/status/PufferBlow/pypufferblow/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/PufferBlow/pypufferblow/actions)
[![GitHub Stars](https://img.shields.io/github/stars/PufferBlow/pypufferblow?style=flat-square&color=yellow)](https://github.com/PufferBlow/pypufferblow/stargazers)

</div>

---

## Overview

`pypufferblow` gives you a clean Python interface to any self-hosted Pufferblow instance. It covers everything from basic API calls to a full decorator-style bot framework for building interactive bots.

```
pip install pypufferblow
```

---

## Quick Start

```python
from pypufferblow import Client, ClientOptions

client = Client(ClientOptions(
    instance="https://chat.example.org",
    username="alice",
    password="secret",
))

client.users.sign_in()

channels = client.channels()
channels.send_message(channel_id="general", message="Hello, world!")
```

---

## Installation

```bash
pip install pypufferblow
```

Or with Poetry:

```bash
poetry add pypufferblow
```

**Requirements:** Python 3.11 or later.

---

## Client API

### Authentication

```python
client.users.sign_in()        # sign in with credentials from ClientOptions
client.users.sign_up()        # register a new account
```

### Users

```python
users = client.users()
users.update_username("new_name")
users.update_status("online")
users.update_password("new_pass")
users.list_users()
```

### Channels

```python
channels = client.channels()

channels.list_channels()
channels.send_message(channel_id, "text")
channels.send_message(channel_id, "text", attachments=["image.png"])
channels.load_messages(channel_id)
channels.mark_as_read(channel_id, message_id)
```

### Real-time WebSocket

```python
ws = client.websocket()

def on_message(msg):
    print(msg.message, msg.attachments)

ws.on_message = on_message
ws.connect()   # listens on all accessible channels
```

For a single channel:

```python
ws = client.create_channel_websocket(channel_id="general")
ws.connect()
```

### Federation

```python
federation = client.federation()

federation.follow_remote_account("alice@other-instance.org")
federation.send_direct_message(peer="alice@other-instance.org", message="hi")
messages = federation.load_direct_messages(peer="alice@other-instance.org")
```

### System

```python
system = client.system()
system.get_instance_info()
system.get_instance_stats()
```

---

## Async Support

Every major operation has an async equivalent:

```python
await client.users.sign_in_async()
channels = await client.channels.list_channels_async()
messages = await client.channels.load_messages_async("general")
await client.channels.send_message_async("general", "hello")
```

---

## Bot Framework

`pypufferblow` includes a decorator-style bot framework inspired by Discord.py.

### Minimal example

```python
from pypufferblow import Bot, BotOptions

bot = Bot(BotOptions(
    instance="https://chat.example.org",
    username="my_bot",
    password="secret",
    command_prefix="!",
))

@bot.command("ping")
def ping(ctx):
    ctx.reply("pong")

bot.run()
```

### Lifecycle hooks

```python
@bot.startup()
def on_startup(ctx):
    print("starting up")

@bot.connect()
def on_connect(ctx):
    print("websocket connected")

@bot.started()
def on_started(ctx):
    print("bot is ready")

@bot.shutdown()
def on_shutdown(ctx):
    print("shutting down")
```

### Message filtering

```python
@bot.message(startswith="!")
def observe_commands(ctx):
    print("incoming command:", ctx.content)

@bot.message(contains="hello")
def greet(ctx):
    ctx.reply(f"Hello, {ctx.author_name}!")
```

### Typed command parameters

```python
@bot.command("ban")
def ban_user(ctx, user_id: str, delete_days: int = 0, notify: bool = True):
    ctx.reply(f"banned {user_id} (delete_days={delete_days}, notify={notify})")

@bot.command("say")
def say(ctx, *parts: str):
    ctx.reply(" ".join(parts))
```

### Command groups

```python
admin = bot.group("admin", aliases=("mod",))

@admin.command("ban")
def ban(ctx, user_id: str):
    ctx.reply(f"banned {user_id}")

@admin.command("announce")
def announce(ctx, *parts: str):
    ctx.reply(" ".join(parts))
```

Responds to `!admin ban <id>` and `!mod announce <text>`.

### Cooldowns and checks

```python
@bot.cooldown(rate=1, per=30, bucket="user")
@bot.command("quote")
def quote(ctx):
    ctx.reply("one quote per 30 seconds per user")

@bot.check(lambda ctx: ctx.author_name != "blocked-user")
@bot.command("hello")
def hello(ctx):
    ctx.reply("hi")
```

### Background loops

```python
@bot.loop(seconds=60, wait_until_ready=True)
def heartbeat(ctx):
    print("alive on", ctx.bot.options.instance_url)
```

### Waiting for events

```python
msg_ctx = await bot.wait_for(
    "message",
    check=lambda ctx: ctx.content == "!ready",
    timeout=30,
)
await msg_ctx.reply_async("acknowledged")

await bot.wait_until_ready()
```

### Built-in help command

```python
bot.install_help_command()
print(bot.format_help())
print(bot.format_help("ping"))
```

### Verbose logging

```python
bot = Bot(BotOptions(
    instance="https://chat.example.org",
    username="my_bot",
    password="secret",
    verbose=True,
))
```

Outputs human-readable logs:

```
14:02:11 | INFO  | bot | Starting bot user=my_bot instance=https://chat.example.org
14:02:11 | INFO  | bot | Websocket connected; bot is ready
14:02:15 | DEBUG | bot | Matched command name=ping author=alice args=[]
```

---

## Bot Context Reference

Every handler receives a `BotContext` object:

| Property / Method | Description |
|---|---|
| `ctx.content` | Full message text |
| `ctx.command_text` | Text after the command name |
| `ctx.author_id` | Sender's user ID |
| `ctx.author_name` | Sender's username |
| `ctx.channel_id` | Channel the message arrived in |
| `ctx.reply("text")` | Send a reply to the same channel |
| `await ctx.reply_async("text")` | Async reply |
| `ctx.send(channel_id, "text")` | Send to a specific channel |
| `ctx.mark_as_read()` | Mark the message as read |

---

## Connecting to a Local Instance

```python
ClientOptions(
    host="localhost",
    port=7575,
    username="admin",
    password="secret",
)
```

`host` + `port` and `instance` (URL) are both accepted.

---

## License

Released under the [GNU General Public License v3.0](LICENSE).
