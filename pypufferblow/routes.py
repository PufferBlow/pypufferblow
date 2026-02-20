from pypufferblow.models.route_model import Route

__all__ = [
    "users_routes",
    "channels_routes",
    "storage_routes",
    "system_routes",
    "admin_routes",
    "decentralized_auth_routes",
    "federation_routes",
    "direct_messages_routes",
]

base_route = "/api/v1"

users_base_route = f"{base_route}/users"
users_routes: list[Route] = [
    Route(f"{users_base_route}/signin", methods=["GET"]),
    Route(f"{users_base_route}/signup", methods=["POST"]),
    Route(f"{users_base_route}/profile", methods=["POST", "PUT"]),
    Route(f"{users_base_route}/profile/reset-auth-token", methods=["POST"]),
    Route(f"{users_base_route}/list", methods=["GET"]),
    Route(f"{users_base_route}/profile/avatar", methods=["POST"]),
    Route(f"{users_base_route}/profile/banner", methods=["POST"]),
]

channels_base_route = f"{base_route}/channels"
channels_routes: list[Route] = [
    Route(f"{channels_base_route}/list/", methods=["POST"]),
    Route(f"{channels_base_route}/create/", methods=["POST"]),
    Route(f"{channels_base_route}/{{channel_id}}/delete", methods=["DELETE"]),
    Route(f"{channels_base_route}/{{channel_id}}/add_user", methods=["PUT"]),
    Route(f"{channels_base_route}/{{channel_id}}/remove_user", methods=["DELETE"]),
    Route(f"{channels_base_route}/{{channel_id}}/load_messages", methods=["GET"]),
    Route(f"{channels_base_route}/{{channel_id}}/send_message", methods=["POST"]),
    Route(f"{channels_base_route}/{{channel_id}}/mark_message_as_read", methods=["PUT"]),
    Route(f"{channels_base_route}/{{channel_id}}/delete_message", methods=["DELETE"]),
]

storage_base_route = f"{base_route}/storage"
storage_routes: list[Route] = [
    Route(f"{storage_base_route}/upload", methods=["POST"]),
    Route(f"{storage_base_route}/files", methods=["POST"]),
    Route(f"{storage_base_route}/delete-file", methods=["POST"]),
    Route(f"{storage_base_route}/file-info", methods=["POST"]),
    Route(f"{storage_base_route}/cleanup-orphaned", methods=["POST"]),
    Route(f"{storage_base_route}/file/{{file_path:path}}", methods=["GET"]),
]

system_base_route = f"{base_route}/system"
system_routes: list[Route] = [
    Route(f"{system_base_route}/latest-release", methods=["GET"]),
    Route(f"{system_base_route}/server-stats", methods=["GET"]),
    Route(f"{system_base_route}/server-info", methods=["GET", "PUT"]),
    Route(f"{system_base_route}/server-usage", methods=["POST"]),
    Route(f"{system_base_route}/server-overview", methods=["POST"]),
    Route(f"{system_base_route}/activity-metrics", methods=["POST"]),
    Route(f"{system_base_route}/recent-activity", methods=["POST"]),
    Route(f"{system_base_route}/logs", methods=["POST"]),
    Route(f"{system_base_route}/upload-avatar", methods=["POST"]),
    Route(f"{system_base_route}/upload-banner", methods=["POST"]),
    Route(f"{system_base_route}/charts/user-registrations", methods=["POST"]),
    Route(f"{system_base_route}/charts/message-activity", methods=["POST"]),
    Route(f"{system_base_route}/charts/online-users", methods=["POST"]),
    Route(f"{system_base_route}/charts/channel-creation", methods=["POST"]),
    Route(f"{system_base_route}/charts/user-status", methods=["POST"]),
]

admin_routes: list[Route] = [
    Route(f"{base_route}/blocked-ips/list", methods=["POST"]),
    Route(f"{base_route}/blocked-ips/block", methods=["POST"]),
    Route(f"{base_route}/blocked-ips/unblock", methods=["POST"]),
    Route(f"{base_route}/background-tasks/status", methods=["POST"]),
    Route(f"{base_route}/background-tasks/run", methods=["POST"]),
]

decentralized_auth_base_route = f"{base_route}/auth/decentralized"
decentralized_auth_routes: list[Route] = [
    Route(f"{decentralized_auth_base_route}/challenge", methods=["POST"]),
    Route(f"{decentralized_auth_base_route}/verify", methods=["POST"]),
    Route(f"{decentralized_auth_base_route}/introspect", methods=["POST"]),
    Route(f"{decentralized_auth_base_route}/revoke", methods=["POST"]),
]

federation_base_route = f"{base_route}/federation"
federation_routes: list[Route] = [
    Route(f"{federation_base_route}/follow", methods=["POST"]),
]

direct_messages_base_route = f"{base_route}/dms"
direct_messages_routes: list[Route] = [
    Route(f"{direct_messages_base_route}/send", methods=["POST"]),
    Route(f"{direct_messages_base_route}/messages", methods=["GET"]),
]
