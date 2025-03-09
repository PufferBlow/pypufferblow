from pypufferblow.client import Client, ClientOptions

def test_client():
    """
    Test the Client object.
    """
    client_options = ClientOptions(
        username="r0d",
        password="12345678"
    )
    
    client = Client(client_options)
