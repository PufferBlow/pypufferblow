
__all__ = [
    "Users",
    "UsersOptions"
]

# Routes
from pypufferblow.routes import users_routes

# Exceptions
from pypufferblow.exceptions import (
    UsernameNotFound,
    InvalidPassword,
    UsernameAlreadyExists
)

# Models
from pypufferblow.models.route_model import Route
from pypufferblow.models.options_model import OptionsModel

class Users: ...
class UsersOptions: ...

class Users:
    """
    The underline class for managing the users routes.
    """
    API_ROUTES: list[Route] = users_routes
    
    SIGNIN_API_ROUTE: Route = users_routes[0]
    SIGNUP_API_ROUTE: Route = users_routes[1]
    PROFILE_API_ROUTE: Route = users_routes[2]
    RESET_AUTH_TOKEN_API_ROUTE: Route = users_routes[3]
    LIST_USERS_API_ROUTE: Route = users_routes[4]
    
    def __init__(self, options: UsersOptions) -> None:
        self.options = options
        self.host = options.host
        self.port = options.port
        self.username = options.username
        self.password = options.password
        self.auth_token = options.auth_token

    def signup(self) -> None: ...
    def signin(self) -> None: ...
    def get_user_profile(self) -> None: ...
    def update_username(self) -> None: ...
    def update_user_status(self) -> None: ...
    def update_user_password(self) -> None: ...
    def reset_user_auth_token(self) -> None: ...

class UsersOptions(OptionsModel):
    """
    Users options
    """
    pass
