
__all__ = [
    "Client",
    "ClientOptions"
]

# Channels class
from pypufferblow.channels import (
    Channels,
    ChannelsOptions
)

# WebSocket class
from pypufferblow.websocket import (
    GlobalWebSocket,
    ChannelWebSocket,
    create_global_websocket,
    create_channel_websocket
)

# User class
from pypufferblow.users import (
    Users,
    UsersOptions
)

# CDN class
from pypufferblow.cdn import (
    CDN,
    CDNOptions
)

# System class
from pypufferblow.system import (
    System,
    SystemOptions
)

# Admin class
from pypufferblow.admin import (
    Admin,
    AdminOptions
)
# Decentralized auth class
from pypufferblow.decentralized_auth import (
    DecentralizedAuth,
    DecentralizedAuthOptions,
)
# Federation class
from pypufferblow.federation import (
    Federation,
    FederationOptions,
)

# Models
from pypufferblow.models.user_model import UserModel

# Routes
from pypufferblow.routes import (
    users_routes,
    channels_routes,
    storage_routes,
    system_routes,
    admin_routes,
    decentralized_auth_routes,
    federation_routes,
    direct_messages_routes,
)

# Models
from pypufferblow.models.options_model import OptionsModel

# Exceptions
from pypufferblow.exceptions import (
    UsernameNotFound,
    InvalidPassword,
    FaildToInitChannels
)

class Client:
    """
    The pufferblow client object.

    This class provides methods to interact with the pufferblow API, including user and channel management.

    Attributes:
        users (Users): The Users object for managing users.
        channels (Channels): The Channels object for managing channels.
        cdn (CDN): The CDN object for file management operations.
        system (System): The System object for monitoring and server information.
        admin (Admin): The Admin object for administration operations.
        websocket (GlobalWebSocket): The global websocket for real-time messaging.

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
    cdn: CDN = None
    system: System = None
    admin: Admin = None
    decentralized_auth: DecentralizedAuth = None
    federation: Federation = None
    websocket: GlobalWebSocket = None
    
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
        for route_list in [
            users_routes,
            channels_routes,
            storage_routes,
            system_routes,
            admin_routes,
            decentralized_auth_routes,
            federation_routes,
            direct_messages_routes,
        ]:
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

    def cdn(self) -> CDN:
        """
        Create a CDN object for file management operations.

        The CDN operations require user authentication, so make sure to call users().sign_in() or users().sign_up() first.

        Returns:
            CDN: The CDN object for file operations.

        Example:
            .. code-block:: python

                >>> # First authenticate
                >>> client.users.sign_in()
                >>> cdn = client.cdn()
                >>> files = cdn.list_files("avatars")
        """
        if not self.users.is_signed_in:
            raise Exception("CDN operations require user authentication. Please call users().sign_in() or users().sign_up() first.")

        cdn_options = CDNOptions(
            host=self.host,
            port=self.port,
            auth_token=self.users.user.auth_token
        )
        self.cdn = CDN(cdn_options)

        return self.cdn

    def system(self) -> System:
        """
        Create a System object for system monitoring and information operations.

        The System operations may require user authentication for certain methods, so make sure to call users().sign_in() or users().sign_up() first.

        Returns:
            System: The System object for monitoring operations.

        Example:
            .. code-block:: python

                >>> # First authenticate
                >>> client.users.sign_in()
                >>> system = client.system()
                >>> stats = system.get_server_stats()
        """
        if self.users and self.users.is_signed_in:
            auth_token = self.users.user.auth_token
        else:
            auth_token = None

        system_options = SystemOptions(
            host=self.host,
            port=self.port,
            auth_token=auth_token
        )
        self.system = System(system_options)

        return self.system

    def admin(self) -> Admin:
        """
        Create an Admin object for administration operations.

        The Admin operations require elevated permissions, so make sure to be an admin/server owner and call users().sign_in() or users().sign_up() first.

        Returns:
            Admin: The Admin object for administration operations.

        Example:
            .. code-block:: python

                >>> # First authenticate as admin
                >>> client.users.sign_in()
                >>> admin = client.admin()
                >>> tasks = admin.get_background_tasks_status()
        """
        if not self.users.is_signed_in:
            raise Exception("Admin operations require user authentication. Please call users().sign_in() or users().sign_up() first.")

        admin_options = AdminOptions(
            host=self.host,
            port=self.port,
            auth_token=self.users.user.auth_token
        )
        self.admin = Admin(admin_options)

        return self.admin

    def websocket(self) -> GlobalWebSocket:
        """
        Create a GlobalWebSocket object for real-time messaging.

        The websocket requires user authentication, so make sure to call users().sign_in() or users().sign_up() first.

        Returns:
            GlobalWebSocket: The GlobalWebSocket object for real-time updates.

        Example:
            .. code-block:: python

                >>> # First authenticate
                >>> client.users.sign_in()
                >>> ws = client.websocket()
                >>> def on_message(msg):
                ...     print(f"Received: {msg.message}")
                >>> ws.on_message = on_message
                >>> ws.connect()
        """
        if not self.users.is_signed_in:
            raise Exception("WebSocket requires user authentication. Please call users().sign_in() or users().sign_up() first.")

        self.websocket = create_global_websocket(
            auth_token=self.users.user.auth_token,
            host_port=f"{self.host}:{self.port}"
        )

        return self.websocket

    def decentralized_auth(self) -> DecentralizedAuth:
        """
        Create a DecentralizedAuth object for node-aware auth flow.
        """
        if not self.users.is_signed_in:
            raise Exception(
                "Decentralized auth requires user authentication. Please call users().sign_in() first."
            )

        options = DecentralizedAuthOptions(
            host=self.host,
            port=self.port,
            auth_token=self.users.user.auth_token,
        )
        self.decentralized_auth = DecentralizedAuth(options)
        return self.decentralized_auth

    def federation(self) -> Federation:
        """
        Create a Federation object for ActivityPub and cross-instance DM operations.
        """
        if not self.users.is_signed_in:
            raise Exception(
                "Federation operations require user authentication. Please call users().sign_in() first."
            )

        options = FederationOptions(
            host=self.host,
            port=self.port,
            auth_token=self.users.user.auth_token,
        )
        self.federation = Federation(options)
        return self.federation

    def create_channel_websocket(self, channel_id: str) -> ChannelWebSocket:
        """
        Create a ChannelWebSocket object for a specific channel's real-time messaging.

        The websocket requires user authentication.

        Args:
            channel_id (str): The channel ID to connect to.

        Returns:
            ChannelWebSocket: The ChannelWebSocket object for the specific channel.

        Example:
            .. code-block:: python

                >>> # First authenticate
                >>> client.users.sign_in()
                >>> ws = client.create_channel_websocket("channel_id")
                >>> ws.connect()
        """
        if not self.users.is_signed_in:
            raise Exception("WebSocket requires user authentication. Please call users().sign_in() or users().sign_up() first.")

        return create_channel_websocket(
            auth_token=self.users.user.auth_token,
            host_port=f"{self.host}:{self.port}",
            channel_id=channel_id
        )

class ClientOptions(OptionsModel):
    """
    ClientOptions class used for managing the Client object options.
    """
    
    def __init__(self, user: UserModel | None = None, **kwargs):
        """Initialize the instance."""
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
