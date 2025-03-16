
# Client
from pypufferblow.client import Client, ClientOptions

# Channels
from pypufferblow.channels import Channels, ChannelsOptions

# exceptions
from pypufferblow.exceptions import (
    UsernameAlreadyExists,
    UsernameNotFound,
    InvalidPassword,
    InvalidStatusValue,
    BadAuthToken,
    ChannelNotFound,
    UserNotFound
    
)

# Value storage
from tests.conftest import value_storage

def test_list_channels() -> None:
    """
    Test the Channels object list_channels method.
    
    This test will test the Channels object list_channels method.
    """
    client_options = ClientOptions(
        username=value_storage.new_username,
        password=value_storage.new_password
    )
    
    client = Client(client_options)
    
    client.users.user.auth_token = value_storage.auth_token
    
    client.channels()
          
    client.channels.list_channels()

def test_list_channels_bad_auth_token() -> None:
    """
    Test the Channels object list_channels method with a bad auth token.
    
    This test will test the Channels object list_channels method with a bad auth token.
    """
    client_options = ClientOptions(
        username=value_storage.new_username,
        password=value_storage.new_password
    )
    
    client = Client(client_options)
    client.users.user.auth_token = value_storage.bad_formated_auth_token
    
    client.channels()
    
    try:
        client.channels.list_channels()
    except BadAuthToken:
        assert True

def test_get_channel_info() -> None:
    """
    Test the Channels object get_channel_info method.
    
    This test will test the Channels object get_channel_info method.
    """
    ...

def test_get_channel_info_channel_not_found() -> None:
    """
    Test the Channels object get_channel_info method with a non-existent channel.
    
    This test will test the Channels object get_channel_info method with a non-existent channel.
    """
    client_options = ClientOptions(
        username=value_storage.new_username,
        password=value_storage.new_password
    )
    
    client = Client(client_options)
    
    client.users.user.auth_token = value_storage.auth_token
    
    client.channels()
    
    channel_id = "non_existent_channel_id"
    
    try:
        client.channels.get_channel_info(channel_id)
    except ChannelNotFound:
        assert True

# NOTE: These tests needs admin or server owner creds

# def test_create_channel() -> None:
#     """
#     Test the Channels object create_channel method.
    
#     This test will test the Channels object create_channel method.
#     """
#     ...

# def test_create_channel_bad_auth_token() -> None:
#     """
#     Test the Channels object create_channel method with a bad auth token.
    
#     This test will test the Channels object create_channel method with a bad auth token.
#     """
#     client_options = ClientOptions(
#         username=value_storage.new_username,
#         password=value_storage.new_password
#     )
    
#     client = Client(client_options)
    
#     client.users.user.auth_token = value_storage.bad_formated_auth_token
    
#     client.channels()
    
#     channel_name = "new_channel"
    
#     try:
#         client.channels.create_channel(channel_name, is_private=False)
#     except BadAuthToken:
#         assert True

# def test_add_user_to_channel() -> None:
#     """
#     Test the Channels object add_user_to_channel method.
    
#     This test will test the Channels object add_user_to_channel method.
#     """
#     ...


# def test_add_user_to_channel_user_not_found() -> None:
#     """
#     Test the Channels object add_user_to_channel method with a non-existent user.
    
#     This test will test the Channels object add_user_to_channel method with a non-existent user.
#     """
#     client_options = ClientOptions(
#         username=value_storage.new_username,
#         password=value_storage.new_password
#     )
    
#     client = Client(client_options)
    
#     client.users.user.auth_token = value_storage.auth_token
    
#     client.channels()
    
#     channel_id = "valid_channel_id"
#     user_id = "non_existent_user_id"
    
#     try:
#         client.channels.add_user_to_channel(channel_id, user_id)
#     except UserNotFound:
#         assert True

# def test_remove_user_from_channel() -> None:
#     """
#     Test the Channels object remove_user_from_channel method.
    
#     This test will test the Channels object remove_user_from_channel method.
#     """
#     client_options = ClientOptions(
#         username=value_storage.new_username,
#         password=value_storage.new_password
#     )
    
#     client = Client(client_options)
    
#     client.users.user.auth_token = value_storage.auth_token
    
#     client.channels()
    
#     channel_id = "valid_channel_id"
#     user_id = "valid_user_id"
#     client.channels.remove_user_from_channel(channel_id, user_id)
    
# def test_remove_user_from_channel_user_not_found() -> None:
#     """
#     Test the Channels object remove_user_from_channel method with a non-existent user.
    
#     This test will test the Channels object remove_user_from_channel method with a non-existent user.
#     """
#     client_options = ClientOptions(
#         username=value_storage.new_username,
#         password=value_storage.new_password
#     )
    
#     client = Client(client_options)
    
#     client.users.user.auth_token = value_storage.auth_token
    
#     client.channels()
    
#     channel_id = "valid_channel_id"
#     user_id = "non_existent_user_id"
    
#     try:
#         client.channels.remove_user_from_channel(channel_id, user_id)
#     except UserNotFound:
#         assert True
