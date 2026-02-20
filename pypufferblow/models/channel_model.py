
__all__ = [
    "ChannelModel"
]

class ChannelModel:
    """
    A channel model
    """
    channel_id: str
    channel_name: str
    messages_ids: list[str]
    is_private: bool | None = False
    allowed_users: list[str]
    created_at: str
    
    def __init__(
        self,
        channel_id: str | None = None,
        channel_name: str | None = None,
        messages_ids: list[str] | None = None,
        is_private: bool | None = False,
        allowed_users: list[str] | None = None,
        created_at: str | None = None
    ):
        self.channel_id =  channel_id
        self.channel_name =  channel_name
        self.messages_ids =   messages_ids
        self.is_private = is_private
        self.allowed_users =  allowed_users
        self.created_at =  created_at
    
    def __repr__(self):
        return (
            f"ChannelModel(channel_id={self.channel_id}, channel_name={self.channel_name}, messages_ids={self.messages_ids}, "
            f"is_private={self.is_private}, allowed_users={self.allowed_users}, created_at={self.created_at})"
        )
    
    def parse_json(self, data: dict):
        """
        Parse the attributes from a json
        """
        for attr in data:
            self.__setattr__(attr, data[attr])
        return self
