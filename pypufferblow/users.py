
__all__ = [
    "Users",
    "UsersOptions",
    "ONLINE_USER_STATUS",
    "OFFLINE_USER_STATUS",
    "INVISIBLE_USER_STATUS"
]

import requests

# Routes
from pypufferblow.routes import users_routes

# Exceptions
from pypufferblow.exceptions import (
    UsernameNotFound,
    InvalidPassword,
    UsernameAlreadyExists,
    BadAuthToken,
    InvalidStatusValue
)

# Models
from pypufferblow.models.user_model import UserModel
from pypufferblow.models.route_model import Route
from pypufferblow.models.options_model import OptionsModel

class Users: ...
class UsersOptions(OptionsModel): ...

ONLINE_USER_STATUS: str = "ONLINE"
OFFLINE_USER_STATUS: str = "OFFLINE"
INVISIBLE_USER_STATUS: str = "INVISIBLE"

USER_STATUS: list[str] = [
    ONLINE_USER_STATUS,
    OFFLINE_USER_STATUS,
    INVISIBLE_USER_STATUS
]

class Users:
    """
    The underline class for managing the users routes.
    
    Attributes:
        user (UserModel): The user model.
        
        is_signed_in (bool, default: False): The user's sign-in status.
        is_owner (bool, default: False): The user's owner status.
        is_admin (bool, default: False): The user's admin status
        
        API_ROUTES (list[Route]): The list of the API routes.
        SIGNIN_API_ROUTE (Route): The sign-in API route.
        SIGNUP_API_ROUTE (Route): The sign-up API route.
        PROFILE_API_ROUTE (Route): The profile API route.
        RESET_AUTH_TOKEN_API_ROUTE (Route): The reset auth token API route.
        LIST_USERS_API_ROUTE (Route): The list users API route.
        
        
    """
    API_ROUTES: list[Route] = users_routes
    
    SIGNIN_API_ROUTE: Route = users_routes[0]
    SIGNUP_API_ROUTE: Route = users_routes[1]
    PROFILE_API_ROUTE: Route = users_routes[2]
    RESET_AUTH_TOKEN_API_ROUTE: Route = users_routes[3]
    LIST_USERS_API_ROUTE: Route = users_routes[4]
    
    user: UserModel = None
    
    is_signed_in: bool = False
    is_owner: bool = False
    is_admin: bool = False
    
    def __init__(self, options: UsersOptions) -> None:
        """
        Initialize the Users object with the given options.

        Args:
            options (UsersOptions): The options for the Users object, including host, port, username, and password.
        
        Returns:
            None.
        """
        self.options = options
        
        self.host = options.host
        self.port = options.port
        self.username = options.username
        self.password = options.password
        
        self.user = UserModel()

    def sign_up(self) -> None:
        """
        Sign up.
        
        Returns:
            None.
        
        Example:
            .. code-block:: python
            
                >>> client.users.sign_up()
        """
        params = {
            "username": self.username,
            "password": self.password
        }
        
        response = requests.post(
            self.SIGNUP_API_ROUTE.api_route,
            params=params
        )
        
        if response.status_code == 409:
            raise UsernameAlreadyExists(f"The provided username '{self.username}' already exists.")

        self.user.auth_token = response.json().get("auth_token")
        self.user.user_id = self.user.auth_token.split(".")[0]
        
        self.is_signed_in = True
        
        self.user = self.get_user_profile(
            user_id=self.user.user_id
        )
        self.is_owner = self.user.is_owner
        self.is_admin = self.user.is_admin
        
    def sign_in(self) -> str:
        """
        Sign in to the user account.
        
        Returns:
            None.
        
        Example:
            .. code-block:: python
            
                >>> auth_token = client.users.sign_in()
        """
        if self.is_signed_in is not None and self.user.auth_token is not None:
            return self.user.auth_token
        
        params = {
            "username": self.username,
            "password": self.password
        }
        
        response = requests.get(
            self.SIGNIN_API_ROUTE.api_route,
            params=params
        )
        
        if response.status_code == 404:
            raise UsernameNotFound(f"The provided username '{self.username}' doesn't seem to be associated with an account.")
        elif response.status_code == 401:
            raise InvalidPassword("The provided password is incorrect.")
        
        self.user.auth_token = response.json().get("auth_token")
        self.is_signed_in = True
        
        return self.user.auth_token
    
    def get_user_profile(self, user_id: str | None = None) -> UserModel:
        """
        Fetch the current user's profile or an other user on the server.
        
        Args:
            user_id (str, default: None): The user's user_id.
        
        Returns:
            UserModel: A UserModel containing the user's profile.
        
        Example:
            .. code-block:: python
            
                >>> user: UserModel = client.users.get_user_profile()
        """
        params = {
            "user_id": user_id if user_id is not None else self.user.user_id,
            "auth_token": self.user.auth_token
        }
        
        response = requests.get(
            self.PROFILE_API_ROUTE.api_route,
            params=params
        )
        
        if response.status_code == 400:
            raise BadAuthToken(f"The provided auth-token '{self.user.auth_token}' is not correctly formated")
        
        user = UserModel()
        user.parse_json(data=response.json())
    
        return user
    
    def update_username(self, new_username: str) -> None:
        """
        Update the user's username.
        
        Args:
            new_username (str): The new user's username.
        
        Returns:
            None.
        
        Example:
            .. code-block:: python
            
                >>> client.users.update_username(new_username="new_username")
        """
        params = {
            "new_username": new_username,
            "auth_token": self.user.auth_token
        }
        
        response = requests.put(
            self.PROFILE_API_ROUTE.api_route,
            params=params
        )
        
        if response.status_code == 409:
            raise UsernameAlreadyExists(f"The provided username '{self.username}' already exists.") 

        self.user.username = new_username
    
    def update_user_status(self, new_status: str) -> None:
        """
        Update the user's status.
        
        Args:
            new_status (str): The new user's status.
        
        Returns:
            None.
            
        Example:
            .. code-block:: python
            
                >>> from pypufferblow.users import (
                ...    ONLINE_USER_STATUS,
                ...    OFFLINE_USER_STATUS,
                ...    INVISIBLE_USER_STATUS
                ... )
                >>> client.users.update_user_status(
                ...    new_status=ONLINE_USER_STATUS
                ... )
        """
        params = {
            "status": new_status,
            "auth_token": self.user.auth_token
        }
        
        response = requests.put(
            self.PROFILE_API_ROUTE.api_route,
            params=params
        )
        
        if response.status_code == 404:
            raise InvalidStatusValue(
                f"The provided status value '{new_status}' is not supported."
                f"The supported status values are: {', '.join(USER_STATUS)}"
            )
        
        self.user.status = new_status
    
    def update_user_password(self, old_password: str, new_password: str) -> None:
        """
        Update the user's password.
        
        Args:
            old_password (str): The old user's password.
            new_password (str): The new user's password.
        
        Returns:
            None.
        
        Example:
            .. code-block:: python
            
                >>> client.users.update_user_password(
                ...    old_password="OLD_NOT_SECURE_PASSWORD",
                ...    new_password="NEW_SUPER_SECURE_PASSWORD"
                ... )
        """
        params = {
            "old_password": old_password,
            "new_password": new_password,
            "auth_token": self.user.auth_token
        }
        
        response = requests.put(
            self.PROFILE_API_ROUTE.api_route,
            params=params
        )
        
        if response.status_code == 401:
            raise InvalidPassword("The provided password is incorrect.")
    
    def reset_user_auth_token(self) -> None:
        """
        Reset the user's auth_token.
        
        Returns:
            None.
        
        Example:
            .. code-block:: python
            
                >>> client.users.reset_user_auth_token()
        """
        params = {
            "password": self.password,
            "auth_token": self.user.auth_token
        }
        
        response = requests.put(
            self.RESET_AUTH_TOKEN_API_ROUTE.api_route,
            params=params
        )
        
        if response.status_code == 404:
            raise InvalidPassword("The provided password is incorrect.")
        elif response.status_code == 400:
            raise BadAuthToken(f"The provided auth-token '{self.user.auth_token}' is not correctly formated")

        self.user.auth_token = response.json().get("auth_token")
        self.user.auth_token_expire_time = response.json().get("auth_token_expire_time")

    def list_users(self) -> list[UserModel]:
        """
        List all the users.
        
        Args:
            None.
        
        Returns:
            list[UserModel]: A list of UserModel objects.
        """
        params = {
            "auth_token": self.user.auth_token
        }
        
        response = requests.get(
            self.LIST_USERS_API_ROUTE.api_route,
            params=params
        )
        
        if response.status_code == 400:
            raise BadAuthToken(f"The provided auth-token '{self.user.auth_token}' is not correctly formated")

        users = response.json().get("users")
        users = [UserModel().parse_json(data=user) for user in users]
        
        return users
        
class UsersOptions(OptionsModel):
    """
    UsersOptions class used for managing the Users object options.
    """
    pass
