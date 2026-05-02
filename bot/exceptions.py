"""
Custom exception hierarchy for the trading bot.
"""


class TradingBotError(Exception):
    """Base exception for all trading bot errors."""


class APIError(TradingBotError):
    """Raised when the Binance API returns a non-2xx response."""

    def __init__(self, code: int | str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Binance API error [{code}]: {message}")


class NetworkError(TradingBotError):
    """Raised on connection timeouts or DNS failures."""


class ValidationError(TradingBotError):
    """Raised when user-supplied input fails validation."""
