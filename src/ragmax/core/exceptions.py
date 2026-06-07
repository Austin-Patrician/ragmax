class RagmaxError(Exception):
    """Base exception for application-level errors."""


class InvalidRequestError(RagmaxError):
    """Raised when request input is invalid for the application service."""


class NotFoundError(RagmaxError):
    """Raised when an expected resource is not found."""


class ConfigurationError(RagmaxError):
    """Raised when required application configuration is missing or inconsistent."""


class ExternalServiceError(RagmaxError):
    """Raised when an external service integration fails."""
