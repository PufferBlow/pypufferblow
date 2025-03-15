
# Client
from pypufferblow.client import Client, ClientOptions

# Value storage
from tests.conftest import ValueStorage

def test_client_model() -> None:
    """
    Test the Client object.
    """
    client_options = ClientOptions(
        username=ValueStorage.username,
        password=ValueStorage.password
    )
    
    client = Client(client_options)
