"""
WebSocket client for real-time messaging
"""

__all__ = [
    "GlobalWebSocket",
    "ChannelWebSocket",
    "create_global_websocket",
]

import asyncio
import json
import threading
import time
from typing import Callable, Optional
from urllib.parse import urljoin, urlparse

try:
    import websockets
    from websockets.exceptions import ConnectionClosedError, WebSocketException
except ImportError:
    websockets = None
    ConnectionClosedError = WebSocketException = Exception

from pypufferblow.models.message_model import WebSocketMessage


class WebSocketBase:
    """Base class for WebSocket connections"""

    def __init__(self, auth_token: str, host_port: str):
        self.auth_token = auth_token
        self.host_port = host_port
        self.websocket = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 1.0  # seconds
        self.running = False
        self.thread = None

        # Callbacks
        self.on_message: Optional[Callable[[WebSocketMessage], None]] = None
        self.on_connected: Optional[Callable[[], None]] = None
        self.on_disconnected: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None

    def _get_ws_url(self) -> str:
        """Get the WebSocket URL"""
        raise NotImplementedError

    def connect(self) -> None:
        """Connect to WebSocket"""
        if websockets is None:
            raise ImportError("websockets package is required for WebSocket functionality")

        if self.thread and self.thread.is_alive():
            return  # Already connecting/running

        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def disconnect(self) -> None:
        """Disconnect from WebSocket"""
        self.running = False
        if self.websocket:
            asyncio.create_task(self.websocket.close())
        if self.thread:
            self.thread.join(timeout=5)

    def _should_reconnect(self) -> bool:
        """Check if we should attempt reconnection"""
        return (
            self.running
            and self.reconnect_attempts < self.max_reconnect_attempts
        )

    def _run(self) -> None:
        """WebSocket connection loop"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self._websocket_loop())
        except Exception as e:
            if self.on_error:
                self.on_error(e)
        finally:
            loop.close()

    async def _websocket_loop(self) -> None:
        """Main WebSocket event loop"""
        while self._should_reconnect():
            try:
                url = self._get_ws_url()
                async with websockets.connect(url) as websocket:
                    self.websocket = websocket
                    self.is_connected = True
                    self.reconnect_attempts = 0

                    if self.on_connected:
                        self.on_connected()

                    await self._handle_messages()

            except websockets.exceptions.ConnectionClosedError:
                # Normal disconnection
                pass
            except Exception as e:
                if self.on_error:
                    self.on_error(e)

                if self._should_reconnect():
                    delay = self.reconnect_delay * (2 ** self.reconnect_attempts)
                    await asyncio.sleep(delay)
                    self.reconnect_attempts += 1
                else:
                    break
            finally:
                self.is_connected = False
                if self.on_disconnected:
                    self.on_disconnected("Connection lost")

    async def _handle_messages(self) -> None:
        """Handle incoming WebSocket messages"""
        try:
            while self.running:
                message_raw = await self.websocket.recv()
                try:
                    message_data = json.loads(message_raw)
                    if self.on_message:
                        message = WebSocketMessage()
                        message.parse_json(message_data)
                        self.on_message(message)
                except json.JSONDecodeError:
                    # Log or handle non-JSON messages
                    pass
        except websockets.exceptions.ConnectionClosedError:
            pass

    def send_read_confirmation(self, message_id: str, channel_id: str | None = None) -> bool:
        """Send read confirmation"""
        if not self.websocket or not self.is_connected:
            return False

        message_data = {
            "type": "read_confirmation",
            "message_id": message_id,
        }
        if channel_id:
            message_data["channel_id"] = channel_id

        message_json = json.dumps(message_data)

        # Send asynchronously
        asyncio.create_task(self._send(message_json))
        return True

    async def _send(self, message: str) -> None:
        """Send a message through WebSocket"""
        if self.websocket and self.is_connected:
            try:
                await self.websocket.send(message)
            except Exception:
                pass


class GlobalWebSocket(WebSocketBase):
    """WebSocket client for global channel updates"""

    def _get_ws_url(self) -> str:
        """Get global WebSocket URL"""
        protocol = "ws" if not self.host_port.startswith(("localhost", "127.0.0.1")) else "ws"
        return f"{protocol}://{self.host_port}/ws?auth_token={self.auth_token}"


class ChannelWebSocket(WebSocketBase):
    """WebSocket client for specific channel"""

    def __init__(self, channel_id: str, auth_token: str, host_port: str):
        super().__init__(auth_token, host_port)
        self.channel_id = channel_id

    def _get_ws_url(self) -> str:
        """Get channel-specific WebSocket URL"""
        protocol = "ws" if not self.host_port.startswith(("localhost", "127.0.0.1")) else "ws"
        return f"{protocol}://{self.host_port}/ws/channels/{self.channel_id}?auth_token={self.auth_token}"


def create_global_websocket(
    auth_token: str,
    host_port: str,
    on_message: Optional[Callable[[WebSocketMessage], None]] = None,
    on_connected: Optional[Callable[[], None]] = None,
    on_disconnected: Optional[Callable[[str], None]] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
) -> GlobalWebSocket:
    """
    Create a global WebSocket connection

    Args:
        auth_token: User authentication token
        host_port: Host and port (e.g., 'localhost:7575')
        on_message: Callback for incoming messages
        on_connected: Callback when connected
        on_disconnected: Callback when disconnected
        on_error: Callback for errors

    Returns:
        GlobalWebSocket instance
    """
    ws = GlobalWebSocket(auth_token, host_port)
    ws.on_message = on_message
    ws.on_connected = on_connected
    ws.on_disconnected = on_disconnected
    ws.on_error = on_error
    return ws


def create_channel_websocket(
    channel_id: str,
    auth_token: str,
    host_port: str,
    on_message: Optional[Callable[[WebSocketMessage], None]] = None,
    on_connected: Optional[Callable[[], None]] = None,
    on_disconnected: Optional[Callable[[str], None]] = None,
    on_error: Optional[Callable[[Exception], None]] = None,
) -> ChannelWebSocket:
    """
    Create a channel-specific WebSocket connection

    Args:
        channel_id: Channel ID to connect to
        auth_token: User authentication token
        host_port: Host and port (e.g., 'localhost:7575')
        on_message: Callback for incoming messages
        on_connected: Callback when connected
        on_disconnected: Callback when disconnected
        on_error: Callback for errors

    Returns:
        ChannelWebSocket instance
    """
    ws = ChannelWebSocket(channel_id, auth_token, host_port)
    ws.on_message = on_message
    ws.on_connected = on_connected
    ws.on_disconnected = on_disconnected
    ws.on_error = on_error
    return ws
