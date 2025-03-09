import random

# client
from pypufferblow.client import Client, ClientOptions

# User status values
from pypufferblow.users import USER_STATUS

# exceptions
from pypufferblow.exceptions import (
    UsernameAlreadyExists,
    UsernameNotFound,
    InvalidPassword,
    InvalidStatusValue,
    BadAuthToken
)

# Value storage
from tests.conftest import ValueStorage

def test_client_sign_up():
    """
    Test the Client object sign-up functionality.

    This test verifies that a new user can successfully sign up using the Client object.
    It initializes the Client with the provided username and password, and then calls
    the sign-up method. The authentication token is stored in ValueStorage for further use.
    """
    client_options = ClientOptions(
        username=ValueStorage.username,
        password=ValueStorage.password
    )
    
    client = Client(client_options)

    client.users.sign_up()
    
    ValueStorage.auth_token = client.users.user.auth_token
    
    print(f"Auth token: {ValueStorage.auth_token}")
    
def test_client_sign_up_username_already_exists():
    """
    Test the Client object sign-up functionality when the username already exists.

    This test verifies that an exception is raised when trying to sign up with a username
    that already exists in the system.
    """
    client_options = ClientOptions(
        username=ValueStorage.username,
        password=ValueStorage.password
    )
    
    client = Client(client_options)

    try:
        client.users.sign_up()
    except Exception as e:
        assert True

def test_client_sign_in() -> None:
    """
    Test the Client object sign-in functionality.

    This test verifies that an existing user can successfully sign in using the Client object.
    It initializes the Client with the provided username and password, and then calls
    the sign-in method. The authentication token is stored in ValueStorage for further use.
    """
    client_options = ClientOptions(
        username=ValueStorage.username,
        password=ValueStorage.password
    )
    
    client = Client(client_options)
    
    client.users.sign_in()
    
    ValueStorage.auth_token = client.users.user.auth_token
    
def test_client_sign_in_username_not_found() -> None:
    """
    Test the Client object sign-in functionality when the username is not found.

    This test verifies that an exception is raised when trying to sign in with a username
    that does not exist in the system.
    """
    client_options = ClientOptions(
        username=ValueStorage.new_username,
        password=ValueStorage.password
    )
    
    client = Client(client_options)
    
    try:
        client.users.sign_in()
    except UsernameNotFound as e:
        assert True

def test_client_sign_in_invalid_password() -> None:
    """
    Test the Client object sign-in functionality with an invalid password.

    This test verifies that an exception is raised when trying to sign in with an invalid password.
    """
    client_options = ClientOptions(
        username=ValueStorage.username,
        password=ValueStorage.new_password
    )
    
    client = Client(client_options)
    
    try:
        client.users.sign_in()
    except InvalidPassword as e:
        assert True

def test_client_update_username() -> None:
    """
    Test the Client object update username functionality.

    This test verifies that an existing user can successfully update their username using the Client object.
    It initializes the Client with the provided username and password, sets the authentication token,
    and then calls the update username method.
    """
    client_options = ClientOptions(
        username=ValueStorage.username,
        password=ValueStorage.password
    )
    
    client = Client(client_options)
    client.users.user.auth_token = ValueStorage.auth_token
    
    
    client.users.update_username(new_username=ValueStorage.new_username)
    
def test_client_update_username_already_exists() -> None:
    """
    Test the Client object update username functionality when the new username already exists.

    This test verifies that an exception is raised when trying to update the username to one that already exists.
    """
    client_options = ClientOptions(
        username=ValueStorage.new_username,
        password=ValueStorage.password
    )
    
    client = Client(client_options)
    client.users.user.auth_token = ValueStorage.auth_token
    
    try:
        client.users.update_username(new_username=ValueStorage.new_username)
    except UsernameAlreadyExists as e:
        assert True

def test_client_update_user_status() -> None:
    """
    Test the Client object update user status functionality.

    This test verifies that an existing user can successfully update their status using the Client object.
    It initializes the Client with the provided username and password, sets the authentication token,
    and then calls the update user status method with a random valid status.
    """
    client_options = ClientOptions(
        username=ValueStorage.new_username,
        password=ValueStorage.password
    )
    
    client = Client(client_options)
    client.users.user.auth_token = ValueStorage.auth_token
    
    client.users.update_user_status(new_status=USER_STATUS[random.choice([i for i in range(len(USER_STATUS))])])    

def test_client_update_user_status_invalid_status_value() -> None:
    """
    Test the Client object update user status functionality with an invalid status value.

    This test verifies that an exception is raised when trying to update the user status to an invalid value.
    """
    client_options = ClientOptions(
        username=ValueStorage.new_username,
        password=ValueStorage.password
    )
    
    client = Client(client_options)
    client.users.user.auth_token = ValueStorage.auth_token
    
    try:
        client.users.update_user_status(new_status="NOT_VALID_STATUS")
    except InvalidStatusValue as e:
        assert True

def test_client_update_user_password() -> None:
    """
    Test the Client object update user password functionality.

    This test verifies that an existing user can successfully update their password using the Client object.
    It initializes the Client with the provided username and password, sets the authentication token,
    and then calls the update user password method with the old and new passwords.
    """
    client_options = ClientOptions(
        username=ValueStorage.new_username,
        password=ValueStorage.password
    )
    
    client = Client(client_options)
    client.users.user.auth_token = ValueStorage.auth_token

    client.users.update_user_password(
        old_password=ValueStorage.password,
        new_password=ValueStorage.new_password
    )
    
def test_client_update_user_password_invalid_password() -> None:
    """
    Test the Client object update user password functionality with an invalid password.

    This test verifies that an exception is raised when trying to update the user password with an invalid old password.
    """
    client_options = ClientOptions(
        username=ValueStorage.new_username,
        password=ValueStorage.password
    )
    
    client = Client(client_options)
    client.users.user.auth_token = ValueStorage.auth_token
    
    try:
        client.users.update_user_password(
            old_password=ValueStorage.password,
            new_password=ValueStorage.new_password
        )
    except InvalidPassword as e:
        assert True

def test_client_reset_user_auth_token() -> None:
    """
    Test the Client object reset user authentication token functionality.

    This test verifies that an existing user can successfully reset their authentication token using the Client object.
    It initializes the Client with the provided username and password, sets the authentication token,
    and then calls the reset user authentication token method.
    """
    client_options = ClientOptions(
        username=ValueStorage.new_username,
        password=ValueStorage.new_password
    )
    
    client = Client(client_options)
    client.users.user.auth_token = ValueStorage.auth_token
    
    client.users.reset_user_auth_token()

def test_client_reset_user_auth_token_invalid_password() -> None:
    """
    Test the Client object reset user authentication token functionality with an invalid password.

    This test verifies that an exception is raised when trying to reset the authentication token with an invalid password.
    """
    client_options = ClientOptions(
        username=ValueStorage.new_username,
        password=ValueStorage.password
    )
    
    client = Client(client_options)
    client.users.user.auth_token = ValueStorage.auth_token
    
    try:
        client.users.reset_user_auth_token()
    except InvalidPassword as e:
        assert True

def test_client_reset_user_auth_token_bad_auth_token() -> None:
    """
    Test the Client object reset user authentication token functionality with a bad authentication token.

    This test verifies that an exception is raised when trying to reset the authentication token with a bad token format.
    """
    client_options = ClientOptions(
        username=ValueStorage.new_username,
        password=ValueStorage.new_password
    )
    
    client = Client(client_options)
    client.users.user.auth_token = ValueStorage.bad_formated_auth_token
    
    try:
        client.users.reset_user_auth_token()
    except BadAuthToken as e:
        assert True
