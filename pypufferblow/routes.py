

# Models
from pypufferblow.models.route_model import Route

__all__ = [
    "users_routes",
    "channels_routes",
    "messages_routes",
    "cdn_routes",
    "system_routes",
    "admin_routes"
]

base_route = "/api/v1"

users_base_route = f"{base_route}/users"
users_routes: list[Route] = [
    Route(f"{users_base_route}/signin", methods=["GET"]),
    Route(f"{users_base_route}/signup", methods=["POST"]),
    Route(f"{users_base_route}/profile", methods=["GET", "PUT"]),
    Route(f"{users_base_route}/profile/reset-auth-token", methods=["PUT"]),
    Route(f"{users_base_route}/list", methods=["GET"]),
    Route(f"{users_base_route}/profile/avatar", methods=["POST"]),
    Route(f"{users_base_route}/profile/banner", methods=["POST"]),
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

cdn_base_route = f"{base_route}/cdn"
cdn_routes: list[Route] = [
    Route(f"{cdn_base_route}/upload", methods=["POST"]),
    Route(f"{cdn_base_route}/files", methods=["GET"]),
    Route(f"{cdn_base_route}/delete-file", methods=["POST"]),
    Route(f"{cdn_base_route}/file-info", methods=["GET"]),
    Route(f"{cdn_base_route}/cleanup-orphaned", methods=["POST"]),
    Route(f"{cdn_base_route}/file/{{file_path:path}}", methods=["GET"]),
]

system_base_route = f"{base_route}/system"
system_routes: list[Route] = [
    Route(f"{system_base_route}/latest-release", methods=["GET"]),
    Route(f"{system_base_route}/server-stats", methods=["GET"]),
    Route(f"{system_base_route}/server-info", methods=["GET"]),
    Route(f"{system_base_route}/server-usage", methods=["GET"]),
    Route(f"{system_base_route}/server-overview", methods=["GET"]),
    Route(f"{system_base_route}/activity-metrics", methods=["GET"]),
    Route(f"{system_base_route}/recent-activity", methods=["GET"]),
    Route(f"{system_base_route}/logs", methods=["POST"]),
    Route(f"{system_base_route}/upload-avatar", methods=["POST"]),
    Route(f"{system_base_route}/upload-banner", methods=["POST"]),
    Route(f"{system_base_route}/server-info", methods=["PUT"]),
    Route(f"{system_base_route}/charts/user-registrations", methods=["POST"]),
    Route(f"{system_base_route}/charts/message-activity", methods=["POST"]),
    Route(f"{system_base_route}/charts/online-users", methods=["POST"]),
    Route(f"{system_base_route}/charts/channel-creation", methods=["POST"]),
    Route(f"{system_base_route}/charts/user-status", methods=["POST"]),
]

admin_base_route = f"{base_route}/admin"
admin_routes: list[Route] = [
    Route(f"{base_route}/blocked-ips/list", methods=["GET"]),
    Route(f"{base_route}/blocked-ips/block", methods=["POST"]),
    Route(f"{base_route}/blocked-ips/unblock", methods=["POST"]),
    Route(f"{base_route}/background-tasks/status", methods=["GET"]),
    Route(f"{base_route}/background-tasks/run", methods=["POST"]),
]

messages_routes: list[Route] = [
    Route(f"{base_route}/", methods=[]),
    Route(f"{base_route}/", methods=[]),
    Route(f"{base_route}/", methods=[]),
    Route(f"{base_route}/", methods=[]),
    Route(f"{base_route}/", methods=[])
]
