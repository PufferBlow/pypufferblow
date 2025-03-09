

# Models
from pypufferblow.models.route_model import Route

__all__ = [
    "users_routes",
    "channels_routes",
    "messages_routes"
]

base_route = "/api/v1"

users_base_route = f"{base_route}/users"
users_routes: list[Route] = [
    Route(f"{users_base_route}/signin", methods=["GET"]),
    Route(f"{users_base_route}/signup", methods=["POST"]),
    Route(f"{users_base_route}/profile", methods=["GET", "PUT"]),
    Route(f"{users_base_route}/profile/reset-auth-token", methods=["PUT"]),
    Route(f"{users_base_route}/list", methods=["GET"]),
]

channels_base_route = f"{base_route}/channels"
channels_routes: list[Route] = [
    Route(f"{channels_base_route}/list/", methods=["GET"]),
    Route(f"{channels_base_route}/create/", methods=["POST"]),
    Route(channels_base_route + "/{channel_id}/delete", methods=["DELETE"]),
    Route(channels_base_route + "/{channel_id}/add_user", methods=["POST"]),
    Route(channels_base_route + "/{channel_id}/remove_user", methods=["DELETE"]),
    Route(channels_base_route + "/{channel_id}/load_messages", methods=["GET"]),
    Route(channels_base_route + "/{channel_id}/send_message", methods=["POST"]),
    Route(channels_base_route + "/{channel_id}/mark_message_as_read", methods=["PUT"]),
    Route(channels_base_route + "/{channel_id}/delete_message", methods=["DELETE"]),
]

messages_routes: list[Route] = [
    Route(f"{base_route}/"),
    Route(f"{base_route}/"),
    Route(f"{base_route}/"),
    Route(f"{base_route}/"),
    Route(f"{base_route}/")
]
