
__all__ = [
    "MessageModel"
]

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
    
    def __init__(
        self,
        message_id : str | None = None,
        message: str | None = None,
        sender_user_id : str | None = None,
        channel_id : str | None = None,
        conversation_id : str | None = None,
        sent_at : str | None = None,
    ):
        self.message_id = message_id
        self.message = message
        self.sender_user_id = sender_user_id
        self.channel_id = channel_id
        self.conversation_id = conversation_id
        self.sent_at = sent_at
    
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
    