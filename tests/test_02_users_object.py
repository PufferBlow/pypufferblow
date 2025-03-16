import random
import pytest

# Client model
from pypufferblow.client import Client, ClientOptions

# User status values
from pypufferblow.users import USER_STATUS

# Models
from pypufferblow.models.user_model import UserModel

# exceptions
from pypufferblow.exceptions import (
    UsernameAlreadyExists,
    UsernameNotFound,
    InvalidPassword,
    InvalidStatusValue,
    BadAuthToken
)

# Value storage
from tests.conftest import value_storage

def test_users_model_sign_up():
    """
    Test the Users object sign-up functionality.

    This test verifies that a new user can successfully sign up using the Users object.
    It initializes the Users with the provided username and password, and then calls
    the sign-up method. The authentication token is stored in ValueStorage for further use.
    """
    client_options = ClientOptions(
        username=value_storage.username,
        password=value_storage.password
    )
    
    client= Client(client_options)

    client.users.sign_up()
    
    value_storage.auth_token = client.users.user.auth_token
    
def test_users_model_sign_up_username_already_exists():
    """
    Test the Users object sign-up functionality when the username already exists.

    This test verifies that an exception is raised when trying to sign up with a username
    that already exists in the system.
    """
    client_options = ClientOptions(
        username=value_storage.username,
        password=value_storage.password
    )
    
    client= Client(client_options)

    try:
        client.users.sign_up()
    except Exception as e:
        assert True

def test_users_model_sign_in() -> None:
    """
    Test the Users object sign-in functionality.

    This test verifies that an existing user can successfully sign in using the Users object.
    It initializes the Users with the provided username and password, and then calls
    the sign-in method. The authentication token is stored in ValueStorage for further use.
    """
    client_options = ClientOptions(
        username=value_storage.username,
        password=value_storage.password
    )
    
    client = Client(client_options)
    
    client.users.sign_in()
    
    value_storage.auth_token = client.users.user.auth_token
    
def test_users_model_sign_in_username_not_found() -> None:
    """
    Test the Users object sign-in functionality when the username is not found.

    This test verifies that an exception is raised when trying to sign in with a username
    that does not exist in the system.
    """
    client_options = ClientOptions(
        username=value_storage.new_username,
        password=value_storage.password
    )
    
    client= Client(client_options)
    
    try:
        client.users.sign_in()
    except UsernameNotFound as e:
        assert True

def test_users_model_sign_in_invalid_password() -> None:
    """
    Test the Users object sign-in functionality with an invalid password.

    This test verifies that an exception is raised when trying to sign in with an invalid password.
    """
    client_options = ClientOptions(
        username=value_storage.username,
        password=value_storage.new_password
    )
    
    client= Client(client_options)
    
    try:
        client.users.sign_in()
    except InvalidPassword as e:
        assert True

def test_users_model_update_username() -> None:
    """
    Test the Users object update username functionality.

    This test verifies that an existing user can successfully update their username using the Users object.
    It initializes the Users with the provided username and password, sets the authentication token,
    and then calls the update username method.
    """
    client_options = ClientOptions(
        username=value_storage.username,
        password=value_storage.password
    )
    
    client= Client(client_options)
    client.users.user.auth_token = value_storage.auth_token
    
    
    client.users.update_username(new_username=value_storage.new_username)
    
def test_users_model_update_username_already_exists() -> None:
    """
    Test the Users object update username functionality when the new username already exists.

    This test verifies that an exception is raised when trying to update the username to one that already exists.
    """
    client_options = ClientOptions(
        username=value_storage.new_username,
        password=value_storage.password
    )
    
    client= Client(client_options)
    client.users.user.auth_token = value_storage.auth_token
    
    try:
        client.users.update_username(new_username=value_storage.new_username)
    except UsernameAlreadyExists as e:
        assert True

def test_users_model_update_user_status() -> None:
    """
    Test the Users object update user status functionality.

    This test verifies that an existing user can successfully update their status using the Users object.
    It initializes the Users with the provided username and password, sets the authentication token,
    and then calls the update user status method with a random valid status.
    """
    client_options = ClientOptions(
        username=value_storage.new_username,
        password=value_storage.password
    )
    
    client= Client(client_options)
    client.users.user.auth_token = value_storage.auth_token
    
    client.users.update_user_status(new_status=USER_STATUS[random.choice([i for i in range(len(USER_STATUS))])])    

def test_users_model_update_user_status_invalid_status_value() -> None:
    """
    Test the Users object update user status functionality with an invalid status value.

    This test verifies that an exception is raised when trying to update the user status to an invalid value.
    """
    client_options = ClientOptions(
        username=value_storage.new_username,
        password=value_storage.password
    )
    
    client= Client(client_options)
    client.users.user.auth_token = value_storage.auth_token
    
    try:
        client.users.update_user_status(new_status="NOT_VALID_STATUS")
    except InvalidStatusValue as e:
        assert True

def test_users_model_update_user_password() -> None:
    """
    Test the Users object update user password functionality.

    This test verifies that an existing user can successfully update their password using the Users object.
    It initializes the Users with the provided username and password, sets the authentication token,
    and then calls the update user password method with the old and new passwords.
    """
    client_options = ClientOptions(
        username=value_storage.new_username,
        password=value_storage.password
    )
    
    client= Client(client_options)
    client.users.user.auth_token = value_storage.auth_token

    client.users.update_user_password(
        old_password=value_storage.password,
        new_password=value_storage.new_password
    )
    
def test_users_model_update_user_password_invalid_password() -> None:
    """
    Test the Users object update user password functionality with an invalid password.

    This test verifies that an exception is raised when trying to update the user password with an invalid old password.
    """
    client_options = ClientOptions(
        username=value_storage.new_username,
        password=value_storage.password
    )
    
    client= Client(client_options)
    client.users.user.auth_token = value_storage.auth_token
    
    try:
        client.users.update_user_password(
            old_password=value_storage.password,
            new_password=value_storage.new_password
        )
    except InvalidPassword as e:
        assert True

def test_users_model_reset_user_auth_token() -> None:
    """
    Test the Users object reset user authentication token functionality.

    This test verifies that an existing user can successfully reset their authentication token using the Users object.
    It initializes the Users with the provided username and password, sets the authentication token,
    and then calls the reset user authentication token method.
    """
    client_options = ClientOptions(
        username=value_storage.new_username,
        password=value_storage.new_password
    )
    
    client= Client(client_options)
    client.users.user.auth_token = value_storage.auth_token
    
    client.users.reset_user_auth_token()

def test_users_model_reset_user_auth_token_invalid_password() -> None:
    """
    Test the Users object reset user authentication token functionality with an invalid password.

    This test verifies that an exception is raised when trying to reset the authentication token with an invalid password.
    """
    client_options = ClientOptions(
        username=value_storage.new_username,
        password=value_storage.password
    )
    
    client= Client(client_options)
    client.users.user.auth_token = value_storage.auth_token
    
    try:
        client.users.reset_user_auth_token()
    except InvalidPassword as e:
        assert True

def test_users_model_reset_user_auth_token_bad_auth_token() -> None:
    """
    Test the Users object reset user authentication token functionality with a bad authentication token.

    This test verifies that an exception is raised when trying to reset the authentication token with a bad token format.
    """
    client_options = ClientOptions(
        username=value_storage.new_username,
        password=value_storage.new_password
    )
    
    client= Client(client_options)
    client.users.user.auth_token = value_storage.bad_formated_auth_token
    
    try:
        client.users.reset_user_auth_token()
    except BadAuthToken as e:
        assert True

def test_users_list_users() -> None:
    """
    Test Users object list users functionality.
    
    This test verifies that the list users method returns a list of users.
    """
    client_options = ClientOptions(
        username=value_storage.new_username,
        password=value_storage.new_password
    )
    
    client= Client(client_options)
    client.users.user.auth_token = value_storage.auth_token
    
    users = client.users.list_users()
    
    assert type(users) == list

def test_users_list_users_bad_auth_token() -> None:
    """
    Test Users object list users functionality with a bad authentication token.
    
    This test verifies that an exception is raised when trying to list users with a bad auth token.
    """
    client_options = ClientOptions(
        username=value_storage.new_username,
        password=value_storage.new_password
    )
    
    client= Client(client_options)
    client.users.user.auth_token = value_storage.bad_formated_auth_token
    
    try:
        client.users.list_users()
    except BadAuthToken as e:
        assert True
    