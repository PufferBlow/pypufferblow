
# Client
from pypufferblow.client import Client, ClientOptions

# Value storage
from tests.conftest import value_storage

def test_client_model() -> None:
    """
    Test the Client object.
    """
    client_options = ClientOptions(
        username=value_storage.username,
        password=value_storage.password
    )
    
    try:
        client = Client(client_options)
        assert True
    except Exception as e:
        assert False, f"Exception: {e}"


def test_client_model_accepts_instance_url() -> None:
    client_options = ClientOptions(
        instance="https://chat.example.org",
        username=value_storage.username,
        password=value_storage.password,
    )

    client = Client(client_options)

    assert client.instance_url == "https://chat.example.org"
    assert client.api_base_url == "https://chat.example.org"
    assert client.ws_base_url == "wss://chat.example.org"
    assert client.users.SIGNIN_API_ROUTE.api_route == "https://chat.example.org/api/v1/users/signin"
