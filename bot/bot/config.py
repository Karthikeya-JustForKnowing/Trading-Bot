"""Configuration helpers for loading Binance testnet credentials."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from .client import TESTNET_BASE_URL
from .exceptions import ValidationError

ENV_PATH = Path(".env")
PLACEHOLDER_PREFIXES = (
    "replace_with_",
    "your_",
    "dummy_",
)


@dataclass(slots=True)
class Settings:
    """Runtime configuration for the CLI application."""

    api_key: str
    api_secret: str
    base_url: str = TESTNET_BASE_URL


def _is_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return any(lowered.startswith(prefix) for prefix in PLACEHOLDER_PREFIXES)


def load_settings(
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Settings:
    """Load configuration from CLI overrides first, then from .env / environment."""
    load_dotenv(ENV_PATH if ENV_PATH.exists() else None)

    resolved_api_key = (api_key or os.getenv("BINANCE_API_KEY", "")).strip()
    resolved_api_secret = (api_secret or os.getenv("BINANCE_API_SECRET", "")).strip()
    resolved_base_url = (base_url or os.getenv("BINANCE_BASE_URL", TESTNET_BASE_URL)).strip()

    if not resolved_api_key or _is_placeholder(resolved_api_key):
        raise ValidationError(
            "Missing Binance API key. Set BINANCE_API_KEY in .env or pass --api-key."
        )
    if not resolved_api_secret or _is_placeholder(resolved_api_secret):
        raise ValidationError(
            "Missing Binance API secret. Set BINANCE_API_SECRET in .env or pass --api-secret."
        )

    return Settings(
        api_key=resolved_api_key,
        api_secret=resolved_api_secret,
        base_url=resolved_base_url or TESTNET_BASE_URL,
    )
