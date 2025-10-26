

__all__ = [
    "Channels",
]

import requests

# Routes
from pypufferblow.routes import channels_routes, cdn_routes

# Exceptions
from pypufferblow.exceptions import (
    BadAuthToken,
    NotAnAdminOrServerOwner,
    ChannelNameAlreadyExists,
    ChannelNotFound,
    UserNotFound,
    FaildToRemoveUserFromChannelUserIsAdmin,
    ExceededMaxMessagesPerPage,
    MessageIsTooLong,
    MessageNotFound
)

# Models
from pypufferblow.models.route_model import Route
from pypufferblow.models.user_model import UserModel
from pypufferblow.models.options_model import OptionsModel
from pypufferblow.models.channel_model import ChannelModel
from pypufferblow.models.message_model import MessageModel

# Channels types
PRIVATE_CHANNEL: int = 0x001
PUBLIC_CHANNEL: int = 0x002

class Channels: ...
class ChannelsOptions(OptionsModel): ...

class Channels:
    """
    The underline class for managing the channels routes.
    
    Attributes:
        API_ROUTES (list[Route]): The list of the API routes.
        LIST_CHANNELS_API_ROUTE (Route): The list channels API route.
        CREATE_CHANNEL_API_ROUTE (Route): The create channel API route.
        DELETE_CHANNEL_API_ROUTE (Route): The delete channel API route.
        ADD_USER_TO_CHANNEL_API_ROUTE (Route): The add user to channel API route.
        REMOVE_USER_FROM_CHANNEL_API_ROUTE (Route): The remove user from channel API route.
        LOAD_MESSAGES_API_ROUTE (Route): The load messages API route.
        SEND_MESSAGE_API_ROUTE (Route): The send message API route.
        MARK_MESSAGE_AS_READ_API_ROUTE (Route): The mark message as read API route.
        DELETE_MESSAGE_API_ROUTE (Route): The delete message API route.
    """
    API_ROUTES: list[Route] = channels_routes
    CDN_API_ROUTES: list[Route] = cdn_routes

    LIST_CHANNELS_API_ROUTE: Route = channels_routes[0]
    CREATE_CHANNEL_API_ROUTE: Route = channels_routes[1]
    DELETE_CHANNEL_API_ROUTE: Route = channels_routes[2]
    ADD_USER_TO_CHANNEL_API_ROUTE: Route = channels_routes[3]
    REMOVE_USER_FROM_CHANNEL_API_ROUTE: Route = channels_routes[4]
    LOAD_MESSAGES_API_ROUTE: Route = channels_routes[5]
    SEND_MESSAGE_API_ROUTE: Route = channels_routes[6]
    MARK_MESSAGE_AS_READ_API_ROUTE: Route = channels_routes[7]
    DELETE_MESSAGE_API_ROUTE: Route = channels_routes[8]

    CDN_UPLOAD_API_ROUTE: Route = cdn_routes[0]
    
    def __init__(self, options: ChannelsOptions) ->None:
        """
        Initialize the Channels object with the given options.

        Args:
            options (ChannelsOptions): The options for the Channels object, including host, port, username, and password.
        """
        self.host = options.host
        self.port = options.port
        self.username = options.username
        self.password = options.password
        
        self.user = options.user
    
    def list_channels(self) -> list[ChannelModel]:
        """
        List the channels.
        
        Args:
            None.
        
        Returns:
            list[ChannelModel]: A list of ChannelModel objects.
        """
        params = {
            "auth_token": self.user.auth_token
        }
        
        response = requests.get(
            self.LIST_CHANNELS_API_ROUTE.api_route,
            params=params
        )
        
        if response.status_code == 400:
            raise BadAuthToken(f"The provided auth-token '{self.user.auth_token}' is not correctly formated")
        
        channels = response.json().get("channels")
        channels = [ChannelModel().parse_json(channel) for channel in channels]
        
        return channels
    
    def get_channel_info(self, channel_id: str) -> ChannelModel:
        """
        Get the channel info.

        Args:
            channel_id (str): The channel's id.

        Returns:
            ChannelModel: A ChannelModel object containing the channel info.

        Example:
            .. code-block:: python

                >>> channel_id = "6da0492c-631e-53f0-8f9f-2cbab5045351"
                >>> channel = client.channels.get_channel_info(channel_id)
        """
        params = {
            "channel_id": channel_id,
            "auth_token": self.user.auth_token
        }

        response = requests.get(
            self.LIST_CHANNELS_API_ROUTE.api_route,
            params=params
        )

        if response.status_code == 400:
            raise BadAuthToken(f"The provided auth-token '{self.user.auth_token}' is not correctly formated")
        elif response.status_code == 404:
            raise ChannelNotFound(f"The provided channel id '{channel_id}' does not exist.")

        channels = response.json().get("channels")
        for channel_data in channels:
            channel = ChannelModel().parse_json(channel_data)
            if channel.channel_id == channel_id:
                return channel

        raise ChannelNotFound(f"The provided channel id '{channel_id}' does not exist.")
    
    def create_channel(self, channel_name: str, is_private: bool | None = False) -> ChannelModel:
        """
        Create a new channel.

        Args:
            channel_name (str): The channel's name.
            is_private (bool, default: False): The channel's type.

        Returns:
            ChannelModel: The created channel.

        Example:
            .. code-block:: python

                >>> channel = client.channels.create_channel(
                ...    "general"
                ... )
        """
        params = {
            "channel_name": channel_name,
            "is_private": is_private,
            "auth_token": self.user.auth_token
        }
        
        if not self.user.is_admin and not self.user.is_server_owner:
            raise NotAnAdminOrServerOwner("Operation not permitted. You are not an admin or a server owner.")

        response = requests.post(
            self.CREATE_CHANNEL_API_ROUTE.api_route,
            params=params
        )
        
        if response.status_code == 403:
            raise NotAnAdminOrServerOwner("Operation not permitted. You are not an admin or a server owner.")
        elif response.status_code == 409:
            raise ChannelNameAlreadyExists(f"The provided channel name '{channel_name}' already existrs. Please change it and try again.")
        elif response.status_code == 400:
            raise BadAuthToken(f"The provided auth-token '{self.user.auth_token}' is not correctly formated")
        
        channel_data = response.json().get("channel_data")
        channel = ChannelModel().parse_json(channel_data)

        return channel
    
    def delete_channel(self, channel_id: str) -> None:
        """
        Delete a channel.
        
        Args:
            channel_id (str): The channel's id.
            
        Returns:
            None.
        
        Example:
            .. code-block:: python

                >>> channel_id = "6da0492c-631e-53f0-8f9f-2cbab5045351"
                >>> client.channels.delete_channel("channel_id")
        """
        params = {
            "channel_id": channel_id,
            "auth_token": self.user.auth_token
        }
        
        if not self.user.is_admin and not self.user.is_server_owner:
            raise NotAnAdminOrServerOwner("Operation not permitted. You are not an admin or a server owner.")
    
        response = requests.delete(
            self.DELETE_CHANNEL_API_ROUTE.api_route,
            params=params
        )
        
        if response.status_code == 403:
            raise NotAnAdminOrServerOwner("Operation not permitted. You are not an admin or a server owner.")
        elif response.status_code == 404:
            raise ChannelNotFound(f"The provided channel id '{channel_id}' does not exist.")
        elif response.status_code == 400:
            raise BadAuthToken(f"The provided auth-token '{self.user.auth_token}' is not correctly formated")
        
    def add_user(self, channel_id: str, user_id: str) -> None:
        """
        Add a user to a channel.
        
        Args:
            channel_id (str): The channel's id.
            user_id (str): The user's id.
        
        Returns:
            None.
        
        Example:
            .. code-block:: python
            
                >>> channel_id = "6da0492c-631e-53f0-8f9f-2cbab5045351"
                >>> user_id = "9ad0dc2f-536v-43f5-x6g4-2dfbh564234"
                >>> client.channels.add_user(channel_id, user_id)
        """
        params = {
            "channel_id": channel_id,
            "user_id": user_id,
            "auth_token": self.user.auth_token
        }
        
        if not self.user.is_admin and not self.user.is_server_owner:
            raise NotAnAdminOrServerOwner("Operation not permitted. You are not an admin or a server owner.")
        
        response = requests.post(
            self.ADD_USER_TO_CHANNEL_API_ROUTE.api_route,
            params=params
        )
        
        if response.status_code == 403:
            raise NotAnAdminOrServerOwner("Operation not permitted. You are not an admin or a server owner.")
        elif response.status_code == 404:
            if user_id in response.json().get("detail"):
                raise UserNotFound(f"The provided user id '{user_id}' does not exist.")
            elif channel_id in response.json().get("detail"):
                raise ChannelNotFound(f"The provided channel id '{channel_id}' does not exist.")
        elif response.status_code == 400:
            raise BadAuthToken(f"The provided auth-token '{self.user.auth_token}' is not correctly formated")
        
        if "is not private" in response.json().get("detail"):
            pass
        
    def remove_user(self, channel_id: str, user_id: str) -> None:
        """
        Remove a user from a channel.
        
        Args:
            channel_id (str): The channel's id.
            user_id (str): The user's id.
            
        Returns:
            None.
        
        Example:
            .. code-block:: python
            
                >>> channel_id = "6da0492c-631e-53f0-8f9f-2cbab5045351"
                >>> user_id = "9ad0dc2f-536v-43f5-x6g4-2dfbh564234"
                >>> client.channels.remove_user(channel_id, user_id)
        
        """
        params = {
            "channel_id": channel_id,
            "user_id": user_id,
            "auth_token": self.user.auth_token
        }
        
        if not self.user.is_admin and not self.user.is_server_owner:
            raise NotAnAdminOrServerOwner("Operation not permitted. You are not an admin or a server owner.")
        
        response = requests.post(
            self.REMOVE_USER_FROM_CHANNEL_API_ROUTE.api_route,
            params=params
        )
        
        if response.status_code == 403:
            if "server owner" in response.json().get("detail") or "user is admin":
                raise FaildToRemoveUserFromChannelUserIsAdmin("Operation not permitted. The user is an admin or a server owner.")
            else:
                raise NotAnAdminOrServerOwner("Operation not permitted. You are not an admin or a server owner.")
        elif response.status_code == 404:
            if user_id in response.json().get("detail"):
                raise UserNotFound(f"The provided user id '{user_id}' does not exist.")
            elif channel_id in response.json().get("detail"):
                raise ChannelNotFound(f"The provided channel id '{channel_id}' does not exist.")
        elif response.status_code == 400:
            raise BadAuthToken(f"The provided auth-token '{self.user.auth_token}' is not correctly formated")
        
        if "is not private" in response.json().get("detail"):
            pass
    
    def load_messages(self, channel_id: str) -> list[MessageModel]:
        """
        Load messages from a channel.
        
        Args:
            channel_id (str): The channel's id.
        
        Returns:
            list[MessageModel]: A list of MessageModel objects.
        
        Example:
            .. code-block:: python
            
                >>> channel_id = "6da0492c-631e-53f0-8f9f-2cbab5045351"
                >>> messages = client.channels.load_messages(
                ...    channel_id=channel_id
                ... )
        """
        params = {
            "channel_id": channel_id,
            "auth_token": self.user.auth_token
        }
        
        response = requests.get(
            self.LOAD_MESSAGES_API_ROUTE.api_route,
            params=params
        )
        
        if response.status_code == 404:
            raise ChannelNotFound(f"The provided channel id '{channel_id}' does not exist.")
        elif response.status_code == 400:
            if "messages_per_page" in response.json().get("detail"):
                raise ExceededMaxMessagesPerPage("The number of messages per page exceeds the maximum limit.")
            else:
                raise BadAuthToken(f"The provided auth-token '{self.user.auth_token}' is not correctly formated")
        
        messages = response.json().get("messages")
        messages = [MessageModel().parse_json(message) for message in messages]

        return messages

    def upload_file(self, file_path: str | None = None, file_data: bytes | None = None, filename: str | None = None, directory: str = "uploads") -> str:
        """
        Upload a file to the CDN and get the URL.

        Args:
            file_path (str): Path to the file to upload (alternative to file_data)
            file_data (bytes): File data as bytes (alternative to file_path)
            filename (str): Filename when using file_data (required if not using file_path)
            directory (str): Target directory for upload ("uploads", "images", etc.)

        Returns:
            str: The CDN URL of the uploaded file.

        Example:
            .. code-block:: python

                >>> file_url = client.channels.upload_file(file_path="image.png")
                >>> file_url = client.channels.upload_file(file_data=binary_data, filename="image.png")
        """
        if file_path and file_data:
            raise ValueError("Provide either file_path or file_data, not both")

        if not file_path and not file_data:
            raise ValueError("Provide either file_path or file_data")

        if not file_path and file_data and not filename:
            raise ValueError("filename is required when providing file_data")

        # Prepare multipart form data
        files = {}
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    files['file'] = (file_path.split('/')[-1], f.read())
            except FileNotFoundError:
                raise FileNotFoundError(f"File not found: {file_path}")
            except IOError as e:
                raise IOError(f"Error reading file {file_path}: {e}")
        else:
            # file_data and filename provided
            files['file'] = (filename, file_data)

        data = {
            'auth_token': self.user.auth_token,
            'directory': directory
        }

        response = requests.post(
            self.CDN_UPLOAD_API_ROUTE.api_route,
            files=files,
            data=data
        )

        if response.status_code == 403:
            raise NotAnAdminOrServerOwner("Server owner access required for CDN uploads.")
        elif response.status_code == 400:
            error_detail = response.json().get("detail", "File upload failed")
            raise ValueError(f"Upload failed: {error_detail}")
        elif response.status_code == 404:
            raise BadAuthToken(f"The provided auth-token '{self.user.auth_token}' is not correctly formatted")
        elif response.status_code != 201:
            raise Exception(f"Upload failed with status {response.status_code}: {response.text}")

        result = response.json()
        return result.get("url")

    def send_message(self, channel_id: str, message: str, attachments: list[str] | None = None) -> None:
        """
        Send a message in a channel with optional attachments.

        Args:
            channel_id (str): The channel's id.
            message (str): The message to send.
            attachments (list[str], optional): List of file paths to attach to the message.

        Returns:
            None.

        Example:
            .. code-block:: python

                >>> channel_id = "6da0492c-631e-53f0-8f9f-2cbab5045351"
                >>> message = "Hello World"
                >>> client.channels.send_message(
                ...    channel_id=channel_id,
                ...    message=message
                ... )

                # With attachments
                >>> client.channels.send_message(
                ...    channel_id=channel_id,
                ...    message="Check this out!",
                ...    attachments=["image.png", "document.pdf"]
                ... )
        """
        # Prepare data for the request
        data = {
            "auth_token": self.user.auth_token,
            "message": message,
        }

        # Prepare multipart form data if attachments are provided
        files = {}
        if attachments:
            for file_path in attachments:
                if not isinstance(file_path, str):
                    raise ValueError(f"All attachments must be file paths (strings), got {type(file_path)}")

                try:
                    files['attachments'] = (file_path.split('/')[-1], open(file_path, 'rb'))
                except FileNotFoundError:
                    raise FileNotFoundError(f"Attachment file not found: {file_path}")
                except IOError as e:
                    raise IOError(f"Error reading attachment file {file_path}: {e}")

        try:
            response = requests.post(
                f"{self.SEND_MESSAGE_API_ROUTE.api_route}/{channel_id}",
                data=data,
                files=files
            )

            if response.status_code == 400:
                if "the message is too long" in response.json().get("detail"):
                    raise MessageIsTooLong("The message is too long")
                else:
                    raise BadAuthToken(f"The provided auth-token '{self.user.auth_token}' is not correctly formatted")
            elif response.status_code == 404:
                raise ChannelNotFound(f"The provided channel id '{channel_id}' does not exist.")

            # Check for successful message send
            if response.status_code != 201:
                try:
                    error_detail = response.json().get("detail", "Unknown error")
                    raise Exception(f"Failed to send message: {error_detail}")
                except:
                    raise Exception(f"Failed to send message: HTTP {response.status_code}")

        finally:
            # Close file handles
            for key, value in files.items():
                if hasattr(value[1], 'close'):
                    value[1].close()
        
    def mark_message_as_read(self, channel_id: str, message_id: str) -> None:
        """
        Mark as a message as being red.
        
        Args:
            channel_id (str): The channel's id.
            message_id (str): The message's id.
            
        Returns:
            None.
        
        Example:
            .. code-block:: python

                >>> channel_id = "6da0492c-631e-53f0-8f9f-2cbab5045351"
                >>> message_id = "9ad0dc2f-536v-43f5-x6g4-2dfbh564234"
                >>> client.channels.mark_message_as_read(
                ...    channel_id=channel_id,
                ...    message_id=message_id
                ... )
        """
        params = {
            "channel_id": channel_id,
            "message_id": message_id,
            "auth_token": self.user.auth_token
        }
        
        response = requests.put(
            self.MARK_MESSAGE_AS_READ_API_ROUTE.api_route,
            params=params
        )
        
        if response.status_code == 400:
            raise BadAuthToken(f"The provided auth-token '{self.user.auth_token}' is not correctly formated")
        elif response.status_code == 404:
            if "message_id" in response.json().get("detail"):
                raise MessageNotFound(f"The provided message id '{message_id}' does not exists.")
            else:
                raise ChannelNotFound(f"The provided channel id '{channel_id}' does not exists.")
        
    def delete_message(self, channel_id: str, message_id: str):
        """
        Delete a message in a channel.
        
        Args:
            channel_id (str): The channel's id.
            message_id (str): The message's id.
            
        Returns:
            None.
        
        Example:
            .. code-block:: python

                >>> channel_id = "6da0492c-631e-53f0-8f9f-2cbab5045351"
                >>> message_id = "9ad0dc2f-536v-43f5-x6g4-2dfbh564234"
                >>> client.channels.delete_message(
                ...    channel_id=channel_id,
                ...    message_id=message_id
                ... )
        """
        params = {
            "channel_id": channel_id,
            "message_id": message_id,
            "auth_token": self.user.auth_token
        }
        
        response = requests.delete(
            self.DELETE_MESSAGE_API_ROUTE.api_route,
            params=params
        )
        
        if response.status_code == 400:
            raise BadAuthToken(f"The provided auth-token '{self.user.auth_token}' is not correctly formated")
        elif response.status_code == 401:
            raise NotAnAdminOrServerOwner("Operation not permitted.")
        elif response.status_code == 404:
            if "message_id" in response.json().get("detail"):
                raise MessageNotFound(f"The provided message id '{message_id}' does not exists.")
            else:
                raise ChannelNotFound(f"The provided channel id '{channel_id}' does not exists.")
        
class ChannelsOptions(OptionsModel):
    """
    Channels options
    """  
    def __init__(self, user: UserModel, **kwargs) -> None:
        super().__init__(**kwargs)
        self.user = user
