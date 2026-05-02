"""
Low-level Binance USDT-M Futures REST client.

Responsibilities
----------------
* HMAC-SHA256 request signing
* HTTP session management
* Structured request / response logging
* Translating HTTP / API errors into domain exceptions
"""

import hashlib
import hmac
import time
import urllib.parse
from typing import Any, Optional

import requests

from .exceptions import APIError, NetworkError
from .logging_config import setup_logging

logger = setup_logging().getChild("client")

TESTNET_BASE_URL = "https://testnet.binancefuture.com"
DEFAULT_RECV_WINDOW = 5_000
REQUEST_TIMEOUT = 10


class BinanceFuturesClient:
    """Thread-safe wrapper around the Binance USDT-M Futures REST API."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = TESTNET_BASE_URL,
        recv_window: int = DEFAULT_RECV_WINDOW,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must not be empty.")

        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = base_url.rstrip("/")
        self._recv_window = recv_window
        self._server_time_offset_ms = 0
        self._time_offset_initialized = False

        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "trading-bot/1.0",
            }
        )
        logger.info("BinanceFuturesClient initialized | base_url=%s", self._base_url)

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self._session.close()

    def _timestamp(self) -> int:
        """Current Unix time in milliseconds."""
        return int(time.time() * 1000) + self._server_time_offset_ms

    def _sync_server_time(self) -> None:
        """Synchronize local request timestamps with Binance server time."""
        local_time_ms = int(time.time() * 1000)
        try:
            response = self._session.get(
                f"{self._base_url}/fapi/v1/time",
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            server_time_ms = response.json()["serverTime"]
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network failure during server time sync: %s", exc)
            raise NetworkError(f"Cannot reach Binance API for server time sync: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            logger.error("Timeout during server time sync after %ss", REQUEST_TIMEOUT)
            raise NetworkError(f"Server time sync timed out after {REQUEST_TIMEOUT}s: {exc}") from exc
        except requests.exceptions.HTTPError as exc:
            response = exc.response
            try:
                payload = response.json() if response is not None else {}
                code = payload.get("code", response.status_code if response else "HTTP_ERR")
                message = payload.get("msg", str(exc))
            except Exception:
                code = response.status_code if response is not None else "HTTP_ERR"
                message = str(exc)
            logger.error("API error during server time sync | code=%s message=%s", code, message)
            raise APIError(code=code, message=message) from exc

        self._server_time_offset_ms = server_time_ms - local_time_ms
        self._time_offset_initialized = True
        logger.info(
            "Server time synchronized | serverTime=%s offsetMs=%s",
            server_time_ms,
            self._server_time_offset_ms,
        )

    def _sign(self, params: dict[str, Any]) -> str:
        """Return the HMAC-SHA256 hex digest signature for params."""
        query_string = urllib.parse.urlencode(params)
        return hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        signed: bool = False,
        retry_on_timestamp_error: bool = True,
    ) -> dict[str, Any]:
        """Execute an HTTP request and return the parsed JSON response."""
        url = f"{self._base_url}{endpoint}"
        base_params = dict(params or {})
        params = dict(base_params)

        if signed:
            if not self._time_offset_initialized:
                self._sync_server_time()
            params["timestamp"] = self._timestamp()
            params["recvWindow"] = self._recv_window
            params["signature"] = self._sign(params)

        safe_params = {key: value for key, value in params.items() if key != "signature"}
        logger.debug("HTTP request | method=%s endpoint=%s params=%s", method, endpoint, safe_params)

        try:
            if method.upper() == "GET":
                response = self._session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            elif method.upper() == "POST":
                response = self._session.post(url, data=params, timeout=REQUEST_TIMEOUT)
            elif method.upper() == "DELETE":
                response = self._session.delete(url, params=params, timeout=REQUEST_TIMEOUT)
            else:
                raise ValueError(f"Unsupported HTTP method: {method!r}")

            logger.debug(
                "HTTP response | method=%s endpoint=%s status=%s body=%.500s",
                method,
                endpoint,
                response.status_code,
                response.text,
            )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.ConnectionError as exc:
            logger.error("Network failure | method=%s endpoint=%s error=%s", method, endpoint, exc)
            raise NetworkError(f"Cannot reach Binance API: {exc}") from exc
        except requests.exceptions.Timeout as exc:
            logger.error("Timeout | method=%s endpoint=%s timeout=%ss", method, endpoint, REQUEST_TIMEOUT)
            raise NetworkError(f"Request timed out after {REQUEST_TIMEOUT}s: {exc}") from exc
        except requests.exceptions.HTTPError as exc:
            response = exc.response
            try:
                payload = response.json() if response is not None else {}
                code = payload.get("code", response.status_code if response else "HTTP_ERR")
                message = payload.get("msg", str(exc))
            except Exception:
                code = response.status_code if response is not None else "HTTP_ERR"
                message = str(exc)

            if signed and str(code) == "-1021" and retry_on_timestamp_error:
                logger.warning(
                    "Timestamp drift detected by Binance | endpoint=%s message=%s | resynchronizing and retrying once",
                    endpoint,
                    message,
                )
                self._sync_server_time()
                return self._request(
                    method,
                    endpoint,
                    params=base_params,
                    signed=signed,
                    retry_on_timestamp_error=False,
                )

            logger.error(
                "API error | method=%s endpoint=%s code=%s message=%s",
                method,
                endpoint,
                code,
                message,
            )
            raise APIError(code=code, message=message) from exc

    def ping(self) -> dict[str, Any]:
        """Test connectivity."""
        return self._request("GET", "/fapi/v1/ping")

    def get_server_time(self) -> int:
        """Return Binance server time in milliseconds."""
        data = self._request("GET", "/fapi/v1/time")
        return data["serverTime"]

    def get_exchange_info(self) -> dict[str, Any]:
        """Return full exchange info."""
        return self._request("GET", "/fapi/v1/exchangeInfo")

    def get_ticker_price(self, symbol: str) -> dict[str, Any]:
        """Return the latest ticker price for symbol."""
        return self._request("GET", "/fapi/v1/ticker/price", params={"symbol": symbol})

    def get_account(self) -> dict[str, Any]:
        """Return full account information."""
        return self._request("GET", "/fapi/v2/account", signed=True)

    def get_open_orders(self, symbol: Optional[str] = None) -> list[dict[str, Any]]:
        """Return all open orders, optionally filtered by symbol."""
        params: dict[str, Any] = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/openOrders", params=params, signed=True)

    def get_order(self, symbol: str, order_id: int) -> dict[str, Any]:
        """Query a specific order by symbol and orderId."""
        return self._request(
            "GET",
            "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
            signed=True,
        )

    def cancel_order(self, symbol: str, order_id: int) -> dict[str, Any]:
        """Cancel an open order."""
        return self._request(
            "DELETE",
            "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
            signed=True,
        )

    def place_order(self, **params: Any) -> dict[str, Any]:
        """Place an order via POST /fapi/v1/order."""
        payload = {"newOrderRespType": "RESULT", **params}
        logger.info("Submitting order | params=%s", payload)
        result = self._request("POST", "/fapi/v1/order", params=payload, signed=True)
        logger.info(
            "Order accepted | orderId=%s status=%s",
            result.get("orderId"),
            result.get("status"),
        )
        return result
