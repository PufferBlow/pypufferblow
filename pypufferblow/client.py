
__all__ = [
    "Client"
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
from pypufferblow.models.options_model import OptionsModel

# Exceptions
from pypufferblow.exceptions import (
    UsernameNotFound,
    InvalidPassword
)

class Client: ...
class ClientOptions(OptionsModel): ...

class Client:
    """
    The pufferblow client object.
    """
    users: Users = None
    channels: Channels = None
    
    def __init__(self, options: ClientOptions) -> None:
        self.options = options
        self.host = options.host
        self.port = options.port
        self.username = options.username
        self.password = options.password
        
        # Create Users object
        self.users()
        
        # Create Channels object
        self.channels()

        # Connect to the server
        self._connect()
    
    def _connect(self) -> None:
        """
        Connect to the pufferblow server.
        """
        try:
            auth_token = self.users.sign_in()
            self.options.auth_token = auth_token
        except UsernameNotFound:
            raise UsernameNotFound(f"The provided username '{self.username}' doesn't seem to be associated with an account.")
        except InvalidPassword:
            raise InvalidPassword("The provided password is incorrect.")
    
    def users(self) -> Users:
        """
        Create a Users object
        """
        self.users = Users(self.options.to_users_options())
        
        return self.users

    def channels(self) -> Channels:
        """"
        Create a Channels object
        """
        self.channels = Channels(self.options.to_channels_options())
        
        return self.channels

class ClientOptions(OptionsModel):
    """
    The options for the client.
    """
    is_signed_in: bool = False
    is_admin: bool = False
    is_moderator: bool = False
    
    def __init__(self):
        super().__init__(self)
    
    def to_users_options(self) -> UsersOptions:
        """
        Convert to a UsersOptions object.
        """
        return UsersOptions(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            auth_token=self.auth_token
        )

    def to_channels_options(self) -> ChannelsOptions:
        """
        Convert to ChannelsOptions object.
        """
        return ChannelsOptions(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            auth_token=self.auth_token
        )
