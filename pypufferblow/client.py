
from __future__ import annotations

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
from pypufferblow.models.route_model import Route

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
        system (System): The System object for instance monitoring and community configuration.
        admin (Admin): The Admin object for administration operations.
        websocket (GlobalWebSocket): The global websocket for real-time messaging.

    Example:
        .. code-block:: python

            >>> from pypufferblow.client import Client, ClientOptions
            >>> client_options = ClientOptions(
            ...    instance="https://chat.example.org",
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
            options (ClientOptions): The options for the client, including the
                home instance address plus user credentials.
        
        Returns:
            None.
        """
        self.options = options
        self.scheme = options.scheme
        self.host = options.host
        self.port = options.port
        self.instance = options.instance_url
        self.instance_url = options.instance_url
        self.api_base_url = options.api_base_url
        self.ws_base_url = options.ws_base_url
        self.username = options.username
        self.password = options.password

        # Create Users object
        self.users()

    def _build_routes(self, route_list: list[Route]) -> list[Route]:
        return [
            Route(
                api_route=f"{self.api_base_url}{route.api_route}",
                methods=list(route.methods),
                forward_to=route.forward_to,
            )
            for route in route_list
        ]

    @staticmethod
    def _assign_routes(target: object, routes: list[Route], *attribute_names: str) -> None:
        target.API_ROUTES = routes
        for index, attribute_name in enumerate(attribute_names):
            setattr(target, attribute_name, routes[index])

    
    def users(self) -> Users:
        """
        Create a Users object for communicating with the users routes.
        
        Returns:
            Users: The Users object for managing users.
        """
        self.users = Users(self.options.to_users_options())
        user_routes = self._build_routes(users_routes)
        self._assign_routes(
            self.users,
            user_routes,
            "SIGNIN_API_ROUTE",
            "SIGNUP_API_ROUTE",
            "PROFILE_API_ROUTE",
            "RESET_AUTH_TOKEN_API_ROUTE",
            "LIST_USERS_API_ROUTE",
            "UPLOAD_AVATAR_API_ROUTE",
            "UPLOAD_BANNER_API_ROUTE",
        )
        
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
        channel_routes = self._build_routes(channels_routes)
        storage_api_routes = self._build_routes(storage_routes)
        self._assign_routes(
            self.channels,
            channel_routes,
            "LIST_CHANNELS_API_ROUTE",
            "CREATE_CHANNEL_API_ROUTE",
            "DELETE_CHANNEL_API_ROUTE",
            "ADD_USER_TO_CHANNEL_API_ROUTE",
            "REMOVE_USER_FROM_CHANNEL_API_ROUTE",
            "LOAD_MESSAGES_API_ROUTE",
            "SEND_MESSAGE_API_ROUTE",
            "MARK_MESSAGE_AS_READ_API_ROUTE",
            "DELETE_MESSAGE_API_ROUTE",
        )
        self.channels.STORAGE_API_ROUTES = storage_api_routes
        self.channels.STORAGE_UPLOAD_API_ROUTE = storage_api_routes[0]

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
            instance=self.instance_url,
            auth_token=self.users.user.auth_token
        )
        self.cdn = CDN(cdn_options)
        storage_api_routes = self._build_routes(storage_routes)
        self._assign_routes(
            self.cdn,
            storage_api_routes,
            "UPLOAD_API_ROUTE",
            "LIST_FILES_API_ROUTE",
            "DELETE_FILE_API_ROUTE",
            "FILE_INFO_API_ROUTE",
            "CLEANUP_ORPHANED_API_ROUTE",
            "SERVE_FILE_API_ROUTE",
        )

        return self.cdn

    def system(self) -> System:
        """
        Create a System object for home-instance monitoring and configuration operations.

        The System operations may require user authentication for certain methods, so make sure to call users().sign_in() or users().sign_up() first.

        Returns:
            System: The System object for monitoring operations.

        Example:
            .. code-block:: python

                >>> # First authenticate
                >>> client.users.sign_in()
                >>> system = client.system()
                >>> stats = system.get_instance_stats()
        """
        if self.users and self.users.is_signed_in:
            auth_token = self.users.user.auth_token
        else:
            auth_token = None

        system_options = SystemOptions(
            instance=self.instance_url,
            auth_token=auth_token
        )
        self.system = System(system_options)
        system_api_routes = self._build_routes(system_routes)
        self._assign_routes(
            self.system,
            system_api_routes,
            "LATEST_RELEASE_API_ROUTE",
            "SERVER_STATS_API_ROUTE",
            "SERVER_INFO_API_ROUTE",
            "SERVER_USAGE_API_ROUTE",
            "SERVER_OVERVIEW_API_ROUTE",
            "ACTIVITY_METRICS_API_ROUTE",
            "RECENT_ACTIVITY_API_ROUTE",
            "SERVER_LOGS_API_ROUTE",
            "UPLOAD_AVATAR_API_ROUTE",
            "UPLOAD_BANNER_API_ROUTE",
            "USER_REGISTRATIONS_CHART_API_ROUTE",
            "MESSAGE_ACTIVITY_CHART_API_ROUTE",
            "ONLINE_USERS_CHART_API_ROUTE",
            "CHANNEL_CREATION_CHART_API_ROUTE",
            "USER_STATUS_CHART_API_ROUTE",
        )
        self.system.UPDATE_SERVER_INFO_API_ROUTE = system_api_routes[2]

        return self.system

    def admin(self) -> Admin:
        """
        Create an Admin object for administration operations.

        The Admin operations require elevated permissions on the home instance,
        so make sure to be an admin or server owner and call users().sign_in() or users().sign_up() first.

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
            instance=self.instance_url,
            auth_token=self.users.user.auth_token
        )
        self.admin = Admin(admin_options)
        admin_api_routes = self._build_routes(admin_routes)
        self._assign_routes(
            self.admin,
            admin_api_routes,
            "LIST_BLOCKED_IPS_API_ROUTE",
            "BLOCK_IP_API_ROUTE",
            "UNBLOCK_IP_API_ROUTE",
            "BACKGROUND_TASKS_STATUS_API_ROUTE",
            "BACKGROUND_TASKS_RUN_API_ROUTE",
        )

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
            instance=self.instance_url,
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
            instance=self.instance_url,
            auth_token=self.users.user.auth_token,
        )
        self.decentralized_auth = DecentralizedAuth(options)
        decentralized_auth_api_routes = self._build_routes(decentralized_auth_routes)
        self._assign_routes(
            self.decentralized_auth,
            decentralized_auth_api_routes,
            "CHALLENGE_API_ROUTE",
            "VERIFY_API_ROUTE",
            "INTROSPECT_API_ROUTE",
            "REVOKE_API_ROUTE",
        )
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
            instance=self.instance_url,
            auth_token=self.users.user.auth_token,
        )
        self.federation = Federation(options)
        federation_api_routes = self._build_routes(federation_routes)
        direct_message_api_routes = self._build_routes(direct_messages_routes)
        self.federation.API_ROUTES = [*federation_api_routes, *direct_message_api_routes]
        self.federation.FOLLOW_REMOTE_API_ROUTE = federation_api_routes[0]
        self.federation.SEND_DIRECT_MESSAGE_API_ROUTE = direct_message_api_routes[0]
        self.federation.LOAD_DIRECT_MESSAGES_API_ROUTE = direct_message_api_routes[1]
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
            instance=self.instance_url,
            channel_id=channel_id
        )

class ClientOptions(OptionsModel):
    """
    ClientOptions class used for managing the Client object options.

    Prefer `instance="https://chat.example.org"` for federated/home-instance
    deployments. `host` and `port` remain available for compatibility.
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
            instance=self.instance_url,
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
            instance=self.instance_url,
            username=self.username,
            password=self.password,
            user=self.user
        )
