
__all__ = [
    "UsernameNotFound",
    "InvalidPassword",
    "UsernameAlreadyExists"
]

# Signin exceptions
class UsernameNotFound(Exception): ...
class InvalidPassword(Exception): ...

# Signup exceptions
class UsernameAlreadyExists(Exception): ...
