
__all__ = [
    "Route"
]

class Route:
    """
    API Route model.
    """
    api_route: str = None
    forward_to: str | None = None
    methods: list[str] = list()

    def __init__(self, api_route: str, methods: list[str], forward_to: str | None = None):
        """Initialize the instance."""
        self.api_route = api_route
        self.forward_to = forward_to
        self.methods = methods
