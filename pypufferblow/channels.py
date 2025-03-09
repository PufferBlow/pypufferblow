

__all__ = [
    "Channels",
]

# Routes
from pypufferblow.routes import channels_routes

# Models
from pypufferblow.models.route_model import Route
from pypufferblow.models.options_model import OptionsModel

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
    
    LIST_CHANNELS_API_ROUTE: Route = channels_routes[0]
    CREATE_CHANNEL_API_ROUTE: Route = channels_routes[1]
    DELETE_CHANNEL_API_ROUTE: Route = channels_routes[2]
    ADD_USER_TO_CHANNEL_API_ROUTE: Route = channels_routes[3]
    REMOVE_USER_FROM_CHANNEL_API_ROUTE: Route = channels_routes[4]
    LOAD_MESSAGES_API_ROUTE: Route = channels_routes[5]
    SEND_MESSAGE_API_ROUTE: Route = channels_routes[6]
    MARK_MESSAGE_AS_READ_API_ROUTE: Route = channels_routes[7]
    DELETE_MESSAGE_API_ROUTE: Route = channels_routes[8]
    
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
    
    def list_channels(self) -> None: ...
    def get_channel_info(self) -> None: ...
    def create_channel(self) -> None: ...
    def delete_channel(self) -> None: ...


class ChannelsOptions(OptionsModel):
    """
    Channels options
    """
    pass
