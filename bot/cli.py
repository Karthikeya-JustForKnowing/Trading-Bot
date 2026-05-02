"""CLI entry point for the Binance Futures Testnet trading bot."""

import argparse
import sys
from typing import Optional

from bot.client import BinanceFuturesClient, TESTNET_BASE_URL
from bot.config import load_settings
from bot.exceptions import APIError, NetworkError, ValidationError
from bot.logging_config import LOG_FILE, setup_logging
from bot.orders import OrderManager
from bot.validators import (
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
    validate_time_in_force,
)

logger = setup_logging().getChild("cli")


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Place Binance Futures Testnet orders from the command line.",
    )
    parser.add_argument("--symbol", required=True, help="Trading symbol, for example BTCUSDT")
    parser.add_argument("--side", required=True, help="Order side: BUY or SELL")
    parser.add_argument(
        "--order-type",
        required=True,
        help="Order type: MARKET, LIMIT, STOP, or STOP_MARKET",
    )
    parser.add_argument("--quantity", required=True, help="Order quantity")
    parser.add_argument("--price", help="Limit price. Required for LIMIT and STOP orders")
    parser.add_argument("--stop-price", help="Trigger price. Required for STOP and STOP_MARKET orders")
    parser.add_argument(
        "--time-in-force",
        default="GTC",
        help="Time in force for LIMIT/STOP orders. Default: GTC",
    )
    parser.add_argument("--api-key", help="Override BINANCE_API_KEY from environment")
    parser.add_argument("--api-secret", help="Override BINANCE_API_SECRET from environment")
    parser.add_argument(
        "--base-url",
        default=TESTNET_BASE_URL,
        help=f"API base URL. Default: {TESTNET_BASE_URL}",
    )
    return parser


def _prevalidate_request(args: argparse.Namespace) -> dict[str, object]:
    """Validate the CLI payload before loading credentials or sending a request."""
    order_type = validate_order_type(args.order_type)
    cleaned: dict[str, object] = {
        "symbol": validate_symbol(args.symbol),
        "side": validate_side(args.side),
        "order_type": order_type,
        "quantity": validate_quantity(args.quantity),
        "price": validate_price(args.price, order_type),
        "stop_price": validate_stop_price(args.stop_price, order_type),
        "time_in_force": validate_time_in_force(args.time_in_force),
    }
    return cleaned


def _display_request_summary(request: dict[str, object]) -> None:
    print("Order request summary")
    print("---------------------")
    print(f"Symbol        : {request['symbol']}")
    print(f"Side          : {request['side']}")
    print(f"Order Type    : {request['order_type']}")
    print(f"Quantity      : {request['quantity']}")
    if request["price"] is not None:
        print(f"Price         : {request['price']}")
    if request["stop_price"] is not None:
        print(f"Stop Price    : {request['stop_price']}")
    if request["order_type"] in {"LIMIT", "STOP"}:
        print(f"Time In Force : {request['time_in_force']}")
    print()


def _display_response(response: dict[str, object]) -> None:
    print("Order response")
    print("--------------")
    print(f"Order ID      : {response.get('orderId')}")
    print(f"Status        : {response.get('status')}")
    print(f"Symbol        : {response.get('symbol')}")
    print(f"Side          : {response.get('side')}")
    print(f"Type          : {response.get('type')}")
    print(f"Original Qty  : {response.get('origQty')}")
    print(f"Executed Qty  : {response.get('executedQty')}")
    print(f"Average Price : {response.get('avgPrice')}")
    if response.get("price") not in {None, "", "0", "0.0", "0.00", "N/A"}:
        print(f"Price         : {response.get('price')}")
    if response.get("stopPrice") not in {None, "", "0", "0.0", "0.00", "N/A"}:
        print(f"Stop Price    : {response.get('stopPrice')}")
    print()


def run(args: Optional[list[str]] = None) -> int:
    """Parse CLI args, place the order, and return a process exit code."""
    parser = build_parser()
    parsed_args = parser.parse_args(args=args)

    try:
        validated_request = _prevalidate_request(parsed_args)
        _display_request_summary(validated_request)

        settings = load_settings(
            api_key=parsed_args.api_key,
            api_secret=parsed_args.api_secret,
            base_url=parsed_args.base_url,
        )
        client = BinanceFuturesClient(
            api_key=settings.api_key,
            api_secret=settings.api_secret,
            base_url=settings.base_url,
        )
        manager = OrderManager(client)

        try:
            response = manager.place_order(
                symbol=str(validated_request["symbol"]),
                side=str(validated_request["side"]),
                order_type=str(validated_request["order_type"]),
                quantity=str(validated_request["quantity"]),
                price=validated_request["price"],
                stop_price=validated_request["stop_price"],
                time_in_force=str(validated_request["time_in_force"]),
            )
        finally:
            client.close()

        _display_response(response)
        print("Success: order request was accepted by Binance Futures Testnet.")
        print(f"Log file: {LOG_FILE}")
        return 0

    except ValidationError as exc:
        logger.error("Validation failed: %s", exc)
        print(f"Failure: validation error - {exc}")
        print(f"Log file: {LOG_FILE}")
        return 1
    except APIError as exc:
        logger.error("API error: %s", exc)
        print(f"Failure: Binance API error - {exc}")
        print(f"Log file: {LOG_FILE}")
        return 1
    except NetworkError as exc:
        logger.error("Network error: %s", exc)
        print(f"Failure: network error - {exc}")
        print(f"Log file: {LOG_FILE}")
        return 1
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.exception("Unexpected error")
        print(f"Failure: unexpected error - {exc}")
        print(f"Log file: {LOG_FILE}")
        return 1


if __name__ == "__main__":
    sys.exit(run())
