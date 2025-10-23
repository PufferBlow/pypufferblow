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

# Real-time messaging with WebSocket
ws = client.websocket()
def on_message(msg):
    print(f"Received: {msg.message}")
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
messages = channels.load_messages(channel_id)
```

### WebSocket

Real-time message receiving.

```python
ws = client.websocket()
ws.on_message = lambda msg: print(msg.message)
ws.connect()
```

## Requirements

- Python >= 3.11
- requests
- websockets
- pydantic (for data validation)

## License

GNU 3.0
