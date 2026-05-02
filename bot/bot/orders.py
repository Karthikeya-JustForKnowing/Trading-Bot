"""
High-level order management layer.

OrderManager wraps BinanceFuturesClient with:
* Input validation
* Small business-rule checks
* Rich logging
* A normalized response for the CLI
"""

from decimal import Decimal
from typing import Any, Optional

from .client import BinanceFuturesClient
from .exceptions import ValidationError
from .logging_config import setup_logging
from .validators import (
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
    validate_time_in_force,
)

logger = setup_logging().getChild("orders")


def _parse_response(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract the most useful CLI-friendly fields from the raw API response."""
    avg_price = raw.get("avgPrice") or raw.get("price") or "N/A"
    return {
        "orderId": raw.get("orderId", "N/A"),
        "symbol": raw.get("symbol", "N/A"),
        "side": raw.get("side", "N/A"),
        "type": raw.get("type", "N/A"),
        "status": raw.get("status", "N/A"),
        "origQty": raw.get("origQty", "N/A"),
        "executedQty": raw.get("executedQty", "N/A"),
        "avgPrice": avg_price,
        "price": raw.get("price", "N/A"),
        "stopPrice": raw.get("stopPrice", "N/A"),
        "timeInForce": raw.get("timeInForce", "N/A"),
        "updateTime": raw.get("updateTime", "N/A"),
        "_raw": raw,
    }


class OrderManager:
    """Facade for placing Binance Futures Testnet orders."""

    def __init__(self, client: BinanceFuturesClient) -> None:
        self.client = client

    def place_order(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str | float | Decimal,
        price: Optional[str | float | Decimal] = None,
        stop_price: Optional[str | float | Decimal] = None,
        time_in_force: str = "GTC",
    ) -> dict[str, Any]:
        """Dispatch to the correct concrete order method."""
        order_type = validate_order_type(order_type)

        if order_type == "MARKET":
            return self.place_market_order(symbol=symbol, side=side, quantity=quantity)
        if order_type == "LIMIT":
            return self.place_limit_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                time_in_force=time_in_force,
            )
        if order_type == "STOP":
            return self.place_stop_limit_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                stop_price=stop_price,
                time_in_force=time_in_force,
            )
        if order_type == "STOP_MARKET":
            return self.place_stop_market_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                stop_price=stop_price,
            )
        raise ValidationError(f"Unsupported order type: {order_type}")

    def place_market_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: str | float | Decimal,
    ) -> dict[str, Any]:
        """Place a market order."""
        validated_symbol = validate_symbol(symbol)
        validated_side = validate_side(side)
        validated_quantity = validate_quantity(quantity)

        logger.info(
            "MARKET order requested | symbol=%s side=%s quantity=%s",
            validated_symbol,
            validated_side,
            validated_quantity,
        )

        raw = self.client.place_order(
            symbol=validated_symbol,
            side=validated_side,
            type="MARKET",
            quantity=str(validated_quantity),
        )
        result = _parse_response(raw)
        logger.info(
            "MARKET order completed | orderId=%s status=%s executedQty=%s avgPrice=%s",
            result["orderId"],
            result["status"],
            result["executedQty"],
            result["avgPrice"],
        )
        return result

    def place_limit_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: str | float | Decimal,
        price: str | float | Decimal,
        time_in_force: str = "GTC",
    ) -> dict[str, Any]:
        """Place a limit order."""
        validated_symbol = validate_symbol(symbol)
        validated_side = validate_side(side)
        validated_quantity = validate_quantity(quantity)
        validated_price = validate_price(price, "LIMIT")
        validated_tif = validate_time_in_force(time_in_force)

        logger.info(
            "LIMIT order requested | symbol=%s side=%s quantity=%s price=%s timeInForce=%s",
            validated_symbol,
            validated_side,
            validated_quantity,
            validated_price,
            validated_tif,
        )

        raw = self.client.place_order(
            symbol=validated_symbol,
            side=validated_side,
            type="LIMIT",
            quantity=str(validated_quantity),
            price=str(validated_price),
            timeInForce=validated_tif,
        )
        result = _parse_response(raw)
        logger.info(
            "LIMIT order accepted | orderId=%s status=%s price=%s",
            result["orderId"],
            result["status"],
            result["price"],
        )
        return result

    def place_stop_limit_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: str | float | Decimal,
        price: str | float | Decimal,
        stop_price: str | float | Decimal,
        time_in_force: str = "GTC",
    ) -> dict[str, Any]:
        """Place a stop-limit order."""
        validated_symbol = validate_symbol(symbol)
        validated_side = validate_side(side)
        validated_quantity = validate_quantity(quantity)
        validated_price = validate_price(price, "STOP")
        validated_stop_price = validate_stop_price(stop_price, "STOP")
        validated_tif = validate_time_in_force(time_in_force)

        if validated_side == "BUY" and validated_stop_price <= validated_price:
            logger.warning(
                "BUY stop-limit relationship looks unusual | stopPrice=%s price=%s",
                validated_stop_price,
                validated_price,
            )
        if validated_side == "SELL" and validated_stop_price >= validated_price:
            logger.warning(
                "SELL stop-limit relationship looks unusual | stopPrice=%s price=%s",
                validated_stop_price,
                validated_price,
            )

        logger.info(
            "STOP order requested | symbol=%s side=%s quantity=%s stopPrice=%s price=%s timeInForce=%s",
            validated_symbol,
            validated_side,
            validated_quantity,
            validated_stop_price,
            validated_price,
            validated_tif,
        )

        raw = self.client.place_order(
            symbol=validated_symbol,
            side=validated_side,
            type="STOP",
            quantity=str(validated_quantity),
            price=str(validated_price),
            stopPrice=str(validated_stop_price),
            timeInForce=validated_tif,
        )
        result = _parse_response(raw)
        logger.info(
            "STOP order accepted | orderId=%s status=%s stopPrice=%s price=%s",
            result["orderId"],
            result["status"],
            result["stopPrice"],
            result["price"],
        )
        return result

    def place_stop_market_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: str | float | Decimal,
        stop_price: str | float | Decimal,
    ) -> dict[str, Any]:
        """Place a stop-market order."""
        validated_symbol = validate_symbol(symbol)
        validated_side = validate_side(side)
        validated_quantity = validate_quantity(quantity)
        validated_stop_price = validate_stop_price(stop_price, "STOP_MARKET")

        logger.info(
            "STOP_MARKET order requested | symbol=%s side=%s quantity=%s stopPrice=%s",
            validated_symbol,
            validated_side,
            validated_quantity,
            validated_stop_price,
        )

        raw = self.client.place_order(
            symbol=validated_symbol,
            side=validated_side,
            type="STOP_MARKET",
            quantity=str(validated_quantity),
            stopPrice=str(validated_stop_price),
        )
        result = _parse_response(raw)
        logger.info(
            "STOP_MARKET order accepted | orderId=%s status=%s stopPrice=%s",
            result["orderId"],
            result["status"],
            result["stopPrice"],
        )
        return result
