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

# Initialize client
client_options = ClientOptions(
    host="localhost",
    port=7575,
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

## API Reference

### Client

Main client class that provides access to all SDK features.

```python
client = Client(ClientOptions(host="localhost", port=7575, username="user", password="pass"))
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

### Federation

Follow remote account and exchange DMs across instances.

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
