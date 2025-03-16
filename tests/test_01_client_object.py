
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
