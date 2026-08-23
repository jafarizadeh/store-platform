class EmailAlreadyRegisteredError(Exception):
    """Raised when attempting to register an existing email."""


class InvalidCredentialsError(Exception):
    """Raised for invalid login credentials."""


class InvalidSessionError(Exception):
    """Raised when a session token is missing, expired, revoked, or unknown."""
