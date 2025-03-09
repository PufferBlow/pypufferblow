
__all__ = [
    "UsernameNotFound",
    "InvalidPassword",
    "UsernameAlreadyExists",
    "BadAuthToken",
    "InvalidStatusValue"
]

# Signin exceptions
class UsernameNotFound(Exception): ...
class InvalidPassword(Exception): ...

# Signup exceptions
class UsernameAlreadyExists(Exception): ...

# Auth token exceptions
class BadAuthToken(Exception): ...

# Update user profile
class InvalidStatusValue(Exception): ...
