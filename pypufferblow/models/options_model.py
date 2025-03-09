
__all__ = [
    "OptionsModel"
]

class OptionsModel:
    """
    Options model for the Client and the other objects.
    """
    def __init__(
        self,
        host: str | None = "127.0.0.1",
        port: int | None = 7575,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
