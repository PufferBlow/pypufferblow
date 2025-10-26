
__all__ = [
    "MessageModel",
    "WebSocketMessage"
]

class WebSocketMessage:
    """
    A WebSocket message model for real-time messages
    """
    type: str
    channel_id: str | None = None
    message_id: str | None = None
    sender_user_id: str | None = None
    username: str | None = None
    sender_avatar_url: str | None = None
    sender_status: str | None = None
    sender_roles: list[str] | None = None
    message: str | None = None
    hashed_message: str | None = None
    sent_at: str | None = None
    attachments: list[str] | None = None
    # Legacy fields for backward compatibility
    user_id: str | None = None
    avatar: str | None = None
    content: str | None = None
    timestamp: str | None = None
    status: str | None = None
    error: str | None = None

    def __init__(
        self,
        type: str = "message",
        channel_id: str | None = None,
        message_id: str | None = None,
        sender_user_id: str | None = None,
        username: str | None = None,
        sender_avatar_url: str | None = None,
        sender_status: str | None = None,
        sender_roles: list[str] | None = None,
        message: str | None = None,
        hashed_message: str | None = None,
        sent_at: str | None = None,
        attachments: list[str] | None = None,
        # Legacy fields
        user_id: str | None = None,
        avatar: str | None = None,
        content: str | None = None,
        timestamp: str | None = None,
        status: str | None = None,
        error: str | None = None,
    ):
        self.type = type
        self.channel_id = channel_id
        self.message_id = message_id
        self.sender_user_id = sender_user_id
        self.username = username
        self.sender_avatar_url = sender_avatar_url
        self.sender_status = sender_status
        self.sender_roles = sender_roles
        self.message = message
        self.hashed_message = hashed_message
        self.sent_at = sent_at
        self.attachments = attachments
        self.user_id = user_id
        self.avatar = avatar
        self.content = content
        self.timestamp = timestamp
        self.status = status
        self.error = error

    def __repr__(self):
        return (
            f"WebSocketMessage(type={self.type}, channel_id={self.channel_id}, message_id={self.message_id}, "
            f"sender_user_id={self.sender_user_id}, message={self.message})"
        )

    def parse_json(self, data: dict) -> None:
        """
        Parse the attributes from a JSON dict
        """
        for attr in data:
            self.__setattr__(attr, data[attr])

    def to_dict(self) -> dict:
        """
        Convert to dictionary for JSON serialization
        """
        return {
            attr: getattr(self, attr) for attr in self.__dict__ if getattr(self, attr) is not None
        }

class MessageModel:
    """
    A message model
    """
    message_id              :       str
    message                 :       str  =  None
    sender_user_id          :       str
    channel_id              :       str  =  None
    conversation_id         :       str  =  None
    sent_at                 :       str
    attachments             :       list[str] = None

    def __init__(
        self,
        message_id : str | None = None,
        message: str | None = None,
        sender_user_id : str | None = None,
        channel_id : str | None = None,
        conversation_id : str | None = None,
        sent_at : str | None = None,
        attachments: list[str] | None = None,
    ):
        self.message_id = message_id
        self.message = message
        self.sender_user_id = sender_user_id
        self.channel_id = channel_id
        self.conversation_id = conversation_id
        self.sent_at = sent_at
        self.attachments = attachments
    
    def __repr__(self):
        return (
            f"MessageModel(message_id={self.message_id}, message={self.message}, sender_user_id={self.sender_user_id}, "
            f"channel_id={self.channel_id}, conversation_id={self.conversation_id}, sent_at={self.sent_at})"
        )
    
    def parse_json(self, data: dict) -> None:
        """
        Parse the attributes from a json
        """
        for attr in data:
            self.__setattr__(attr, data[attr])
