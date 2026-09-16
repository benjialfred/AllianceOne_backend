"""
Telegram Integration Exceptions (Fail-Closed Architecture)
"""

class TelegramError(Exception):
    """Base exception for all Telegram integration issues."""
    pass

class TelegramAPIError(TelegramError):
    """Raised when Telegram Bot API returns an error or fails to connect."""
    def __init__(self, message: str, status_code: int = 500, error_code: int = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code

class TelegramConfigurationError(TelegramError):
    """Raised when Telegram configuration (e.g. token) is missing or invalid."""
    pass

class TelegramSecurityError(TelegramError):
    """Raised when an update fails verification or secret token validation."""
    pass

class TelegramIdempotencyError(TelegramError):
    """Raised when an update cannot be logged or duplicate execution is prevented."""
    pass
