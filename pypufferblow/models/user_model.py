
__all__ = [
    "UserModel"
]

class UserModel:
    """
    A user model
    """
    user_id: str
    username: str
    status: str
    last_seen: str | None = None
    joined_servers_ids: list[str] | None = None

    # Role-based permissions (derived from roles_ids)
    is_owner: bool = False
    is_admin: bool = False

    created_at: str
    updated_at: str

    auth_token: str
    raw_auth_token: str | None = None
    auth_token_expire_time: str | None = None

    # Profile customization
    avatar_url: str | None = None
    banner_url: str | None = None
    about: str | None = None

    # Additional API fields
    inbox_id: str | None = None
    origin_server: str | None = None
    roles_ids: list[str] | None = None

    def __init__(
        self,
        user_id: str | None = None,
        username: str| None = None,
        status: str | None = None,
        last_seen: str | None = None,
        joined_servers_ids: list[str] | None = None,

        is_owner: bool | None = False,
        is_admin: bool | None = False,

        created_at: str | None = None,
        updated_at: str | None = None,

        auth_token: str | None = None,
        raw_auth_token: str | None = None,
        auth_token_expire_time: str | None = None,

        avatar_url: str | None = None,
        banner_url: str | None = None,
        about: str | None = None,

        inbox_id: str | None = None,
        origin_server: str | None = None,
        roles_ids: list[str] | None = None,
    ) -> None:
        self.user_id = user_id
        self.username = username
        self.status = status
        self.last_seen = last_seen
        self.joined_servers_ids = joined_servers_ids

        self.is_owner = is_owner
        self.is_admin = is_admin

        self.created_at = created_at
        self.updated_at = updated_at

        self.auth_token = auth_token
        self.raw_auth_token = raw_auth_token
        self.auth_token_expire_time = auth_token_expire_time

        self.avatar_url = avatar_url
        self.banner_url = banner_url
        self.about = about

        self.inbox_id = inbox_id
        self.origin_server = origin_server
        self.roles_ids = roles_ids
    
    def __repr__(self):
        return (
            f"UserModel(user_id={self.user_id!r}, username={self.username!r}, status={self.status!r}, "
            f"last_seen={self.last_seen!r}, joined_servers_ids={self.joined_servers_ids!r}, "
            f"is_owner={self.is_owner!r}, is_admin={self.is_admin!r}, "
            f"created_at={self.created_at!r}, updated_at={self.updated_at!r}, "
            f"avatar_url={self.avatar_url!r}, about={self.about!r}, "
            f"inbox_id={self.inbox_id!r}, origin_server={self.origin_server!r}, roles_ids={self.roles_ids!r})"
        )
    
    def parse_json(self, data: dict):
        """
        Parse the attributes from a json
        """
        for attr in data:
            self.__setattr__(attr, data[attr])
        return self
