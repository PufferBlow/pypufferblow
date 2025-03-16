
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
    last_seen: str
    joined_servers_ids: list[str]
    conversations: list[str]
    contacts: list[str]
    
    is_owner: bool = False
    is_admin: bool = False

    created_at: str
    updated_at: str
    
    auth_token: str
    auth_token_expire_time: str

    def __init__(
        self,
        user_id: str | None = None,
        username: str| None = None,
        status: str | None = None,
        last_seen: str | None = None,
        joined_servers_ids: list[str] | None = None,
        conversations: list[str] | None = list(),
        contacts: list[str]| None = list(),
        
        is_owner: bool | None = False,
        is_admin: bool | None = False,

        created_at: str | None = None,
        updated_at: str | None = None,
        
        auth_token: str | None = None,
        auth_token_expire_time: str | None = None,
    ) -> None:
        self.user_id = user_id
        self.username = username
        self.status = status
        self.last_seen = last_seen
        self.joined_servers_ids = joined_servers_ids
        self.conversations = conversations
        self.contacts = contacts
    
        self.is_owner = is_owner
        self.is_admin = is_admin

        self.created_at = created_at
        self.updated_at = updated_at
    
        self.auth_token = auth_token
        self.auth_token_expire_time = auth_token_expire_time
    
    def __repr__(self):
        return (
            f"UserModel(user_id={self.user_id!r}, username={self.username!r}, status={self.status!r}, "
            f"last_seen={self.last_seen!r}, joined_servers_ids={self.joined_servers_ids!r}, "
            f"conversations={self.conversations!r}, contacts={self.contacts!r}, "
            f"is_owner={self.is_owner!r}, is_admin={self.is_admin!r}, "
            f"created_at={self.created_at!r}, updated_at={self.updated_at!r})"
        )
    
    def parse_json(self, data: dict) -> None:
        """
        Parse the attributes from a json
        """
        for attr in data:
            self.__setattr__(attr, data[attr])
