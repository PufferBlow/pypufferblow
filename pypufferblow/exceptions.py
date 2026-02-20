__all__ = [
    "UsernameNotFound",
    "InvalidPassword",
    "UsernameAlreadyExists",
    "BadAuthToken",
    "InvalidStatusValue",
    "FaildToInitChannels",
    "NotAnAdminOrServerOwner",
    "ChannelNameAlreadyExists",
    "ChannelNotFound",
    "FaildToRemoveUserFromChannelUserIsAdmin",
    "ExceededMaxMessagesPerPage",
    "MessageIsTooLong",
    "MessageNotFound",
    "UserNotFound",
    "FileNotFound",
    "UnsupportedFileType",
    "IPSecurityError",
    "ServerError"
]


class UsernameNotFound(Exception):
    """Raised when a username lookup fails."""


class InvalidPassword(Exception):
    """Raised when an invalid password is provided."""


class UsernameAlreadyExists(Exception):
    """Raised when attempting to create an existing username."""


class BadAuthToken(Exception):
    """Raised when an auth token is invalid or malformed."""


class InvalidStatusValue(Exception):
    """Raised when an unsupported user status value is used."""


class FaildToInitChannels(Exception):
    """Raised when the channels client cannot be initialized."""


class NotAnAdminOrServerOwner(Exception):
    """Raised when privileged actions are attempted without permissions."""


class ChannelNameAlreadyExists(Exception):
    """Raised when creating a channel with a duplicate name."""


class ChannelNotFound(Exception):
    """Raised when a channel could not be found."""


class FaildToRemoveUserFromChannelUserIsAdmin(Exception):
    """Raised when removal of an admin user from a channel is denied."""


class ExceededMaxMessagesPerPage(Exception):
    """Raised when requested messages exceed the allowed page size."""


class MessageIsTooLong(Exception):
    """Raised when a message exceeds server limits."""


class MessageNotFound(Exception):
    """Raised when a message could not be found."""


class UserNotFound(Exception):
    """Raised when a user could not be found."""


class FileNotFound(Exception):
    """Raised when a requested file could not be found."""


class UnsupportedFileType(Exception):
    """Raised when an unsupported file type is provided."""


class IPSecurityError(Exception):
    """Raised for IP security management failures."""


class ServerError(Exception):
    """Raised when server-side operations fail."""
