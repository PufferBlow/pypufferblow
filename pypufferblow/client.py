
__all__ = [
    "Client",
    "ClientOptions"
]

# Channels class
from pypufferblow.channels import (
    Channels,
    ChannelsOptions
)

# User class
from pypufferblow.users import (
    Users,
    UsersOptions
)

# Models
from pypufferblow.models.user_model import UserModel

# Routes
from pypufferblow.routes import (
    users_routes,
    channels_routes,
    messages_routes
)

# Models
from pypufferblow.models.options_model import OptionsModel

# Exceptions
from pypufferblow.exceptions import (
    UsernameNotFound,
    InvalidPassword,
    FaildToInitChannels
)

class Client: ...
class ClientOptions(OptionsModel): ...

class Client:
    """
    The pufferblow client object.
    
    This class provides methods to interact with the pufferblow API, including user and channel management.

    Attributes:
        users (Users): The Users object for managing users.
        channels (Channels): The Channels object for managing channels.
    
    Example:
        .. code-block:: python
        
            >>> from pypufferblow.client import Client, ClientOptions
            >>> client_options = ClientOptions(
            ...    host="localhost",
            ...    port=7575,
            ...    username="user1",
            ...    password="SUPER_SERCRET_PASSWORD"
            ... )
            >>> client = Client(client_options)
    """
    users: Users = None
    channels: Channels = None
    
    def __init__(self, options: ClientOptions) -> None:
        """
        Initialize the Client object with the given options.

        Args:
            options (ClientOptions): The options for the client, including host, port, username, and password.
        
        Returns:
            None.
        """
        self.options = options
        self.host = options.host
        self.port = options.port
        self.username = options.username
        self.password = options.password
        
        # Add the base api route to the routes
        for route_list in [users_routes, channels_routes, messages_routes]:
            for i in range(len(route_list)):
                if self.host not in route_list[i].api_route:
                    route_list[i].api_route = f"http://{self.host}:{self.port}" + route_list[i].api_route
        
        # Create Users object
        self.users()

    
    def users(self) -> Users:
        """
        Create a Users object for communicating with the users routes.
        
        Returns:
            Users: The Users object for managing users.
        """
        self.users = Users(self.options.to_users_options())
        self.users.API_ROUTES = users_routes
        
        return self.users

    def channels(self) -> Channels:
        """
        Create a Channels object for communicating with the channels routes.
        
        Returns:
            Channels: The Channels object for managing channels.
        """
        if self.options.user is None:
            if self.users.user is None:
                raise FaildToInitChannels("Failed to initialize the Channels object."
                                        "Make sure the call on the 'Users.sign_in' or 'Users.sign_up' method to create a user model object.")
            
            self.options.user = self.users.user
        
        self.channels = Channels(self.options.to_channels_options())
        self.channels.API_ROUTES = channels_routes
        
        return self.channels

class ClientOptions(OptionsModel):
    """
    ClientOptions class used for managing the Client object options.
    """
    
    def __init__(self, user: UserModel | None = None, **kwargs):
        super().__init__(**kwargs)
        self.user = user
        
    def to_users_options(self) -> UsersOptions:
        """
        Convert to a UsersOptions object.
        
        Returns:
            UserOptions: The UserOptions object.
        """
        return UsersOptions(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password
        )

    def to_channels_options(self) -> ChannelsOptions:
        """
        Convert to ChannelsOptions object.
        
        Returns:
            ChannelsOptions: The ChannelsOptions object.
        """
        return ChannelsOptions(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            user=self.user
        )
