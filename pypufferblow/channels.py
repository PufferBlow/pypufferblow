

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
        self.host = options.host
        self.port = options.port
        self.username = options.username
        self.password = options.password
        self.auth_token = options.auth_token
    
    def list_channels(self) -> None: ...
    def get_channel_info(self) -> None: ...
    def create_channel(self) -> None: ...
    def delete_channel(self) -> None: ...


class ChannelsOptions(OptionsModel):
    """
    Channels options
    """
    pass
