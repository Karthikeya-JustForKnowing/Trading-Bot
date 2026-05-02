"""
Input validation utilities.

All public functions either return the cleaned / typed value on success or
raise ValidationError with a human-readable message.
"""

from decimal import Decimal, InvalidOperation
from typing import Optional

from .exceptions import ValidationError

VALID_SIDES = frozenset({"BUY", "SELL"})
VALID_ORDER_TYPES = frozenset({"LIMIT", "MARKET", "STOP", "STOP_MARKET"})
NEEDS_PRICE = frozenset({"LIMIT", "STOP"})
NEEDS_STOP_PRICE = frozenset({"STOP", "STOP_MARKET"})
VALID_TIME_IN_FORCE = frozenset({"GTC", "IOC", "FOK", "GTX"})


def validate_symbol(symbol: str) -> str:
    """Return the upper-cased trading pair symbol or raise ValidationError."""
    cleaned = symbol.strip().upper()
    if not cleaned:
        raise ValidationError("Symbol cannot be empty.")
    if not cleaned.isalnum():
        raise ValidationError(
            f"Invalid symbol '{symbol}'. Use an alphanumeric pair like BTCUSDT."
        )
    if len(cleaned) > 20:
        raise ValidationError(f"Symbol '{symbol}' is too long (max 20 characters).")
    return cleaned


def validate_side(side: str) -> str:
    """Return BUY or SELL or raise ValidationError."""
    cleaned = side.strip().upper()
    if cleaned not in VALID_SIDES:
        raise ValidationError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return cleaned


def validate_order_type(order_type: str) -> str:
    """Return the validated order type or raise ValidationError."""
    cleaned = order_type.strip().upper()
    if cleaned not in VALID_ORDER_TYPES:
        raise ValidationError(
            "Invalid order type "
            f"'{order_type}'. Supported types: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return cleaned


def validate_quantity(quantity: str | float | Decimal) -> Decimal:
    """Return a positive Decimal quantity or raise ValidationError."""
    try:
        cleaned = Decimal(str(quantity))
    except InvalidOperation as exc:
        raise ValidationError(
            f"Invalid quantity '{quantity}'. Must be a positive number."
        ) from exc
    if cleaned <= 0:
        raise ValidationError(
            f"Quantity must be greater than zero, got '{quantity}'."
        )
    return cleaned


def validate_price(
    price: Optional[str | float | Decimal],
    order_type: str,
) -> Optional[Decimal]:
    """Validate and return the price for order types that require it."""
    if order_type in NEEDS_PRICE and price is None:
        raise ValidationError(f"Price is required for {order_type} orders.")
    if price is None:
        return None
    try:
        cleaned = Decimal(str(price))
    except InvalidOperation as exc:
        raise ValidationError(
            f"Invalid price '{price}'. Must be a positive number."
        ) from exc
    if cleaned <= 0:
        raise ValidationError(f"Price must be greater than zero, got '{price}'.")
    return cleaned


def validate_stop_price(
    stop_price: Optional[str | float | Decimal],
    order_type: str,
) -> Optional[Decimal]:
    """Validate and return the stop / trigger price."""
    if order_type in NEEDS_STOP_PRICE and stop_price is None:
        raise ValidationError(f"Stop price is required for {order_type} orders.")
    if stop_price is None:
        return None
    try:
        cleaned = Decimal(str(stop_price))
    except InvalidOperation as exc:
        raise ValidationError(
            f"Invalid stop price '{stop_price}'. Must be a positive number."
        ) from exc
    if cleaned <= 0:
        raise ValidationError(
            f"Stop price must be greater than zero, got '{stop_price}'."
        )
    return cleaned


def validate_time_in_force(time_in_force: str) -> str:
    """Return the validated Time-In-Force value or raise ValidationError."""
    cleaned = time_in_force.strip().upper()
    if cleaned not in VALID_TIME_IN_FORCE:
        raise ValidationError(
            "Invalid timeInForce "
            f"'{time_in_force}'. Supported: {', '.join(sorted(VALID_TIME_IN_FORCE))}."
        )
    return cleaned
