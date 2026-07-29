"""Secrets manager — unified access to credentials from env and files."""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class SecretsManager:
    """Read secrets from environment variables or gitignored files.

    Supports the file-based layout documented in ``config/CONFIG.md`` and
    provides a single interface that can be extended to Vault/AWS SM later.
    """

    def __init__(self, project_root: Path | None = None) -> None:
        self._root = project_root or Path.cwd()

    def get_env(self, key: str, default: str = "") -> str:
        return os.environ.get(key, default)

    def get_file(self, relative_path: str, *, strip: bool = True) -> str:
        path = self._root / relative_path
        if not path.exists():
            return ""
        value = path.read_text(encoding="utf-8")
        return value.strip() if strip else value

    def get_upstox_pin(self) -> str:
        pin = self.get_env("UPSTOX_PIN")
        if pin:
            return pin
        file_path = self.get_env("UPSTOX_PIN_FILE", "config/upstox-pin.txt")
        return self.get_file(file_path)

    def get_upstox_totp_secret(self) -> str:
        secret = self.get_env("UPSTOX_TOTP_SECRET")
        if secret:
            return secret
        file_path = self.get_env("UPSTOX_TOTP_SECRET_FILE", "config/upstox-totp-secret.txt")
        return self.get_file(file_path)

    def get_api_key(self) -> str:
        return self.get_env("API_KEY")

    def get_dhan_client_id(self) -> str:
        """Get Dhan client ID from environment variable or file fallback.

        Returns:
            Dhan client ID string. Returns empty string if not found.
        """
        client_id = self.get_env("DHAN_CLIENT_ID")
        if client_id:
            return client_id
        file_path = self.get_env("DHAN_CLIENT_ID_FILE", "config/dhan-client-id.txt")
        return self.get_file(file_path)

    def get_dhan_access_token(self) -> str:
        """Get Dhan access token from environment variable or file fallback.

        Returns:
            Dhan access token string. Returns empty string if not found.
        """
        token = self.get_env("DHAN_ACCESS_TOKEN")
        if token:
            return token
        file_path = self.get_env("DHAN_ACCESS_TOKEN_FILE", "config/dhan-access-token.txt")
        return self.get_file(file_path)

    def get_dhan_totp_secret(self) -> str | None:
        """Get TOTP secret from environment variable or file fallback.

        Returns:
            TOTP secret string, or None if not configured.
        """
        secret = self.get_env("DHAN_TOTP_SECRET")
        if secret:
            return secret
        file_path = self.get_env("DHAN_TOTP_SECRET_FILE", "config/dhan-totp-secret.txt")
        value = self.get_file(file_path)
        return value if value else None

    def get_dhan_pin(self) -> str | None:
        """Get PIN from environment variable or file fallback.

        Returns:
            PIN string, or None if not configured.
        """
        pin = self.get_env("DHAN_PIN")
        if pin:
            return pin
        file_path = self.get_env("DHAN_PIN_FILE", "config/dhan-pin.txt")
        value = self.get_file(file_path)
        return value if value else None

    def get_dhan_environment(self) -> str:
        """Get Dhan environment (LIVE vs SANDBOX).

        Returns:
            Environment string. Defaults to 'LIVE' if not set.
        """
        return self.get_env("DHAN_ENVIRONMENT", "LIVE")

    def require(self, key: str) -> str:
        value = self.get_env(key)
        if not value:
            raise ValueError(f"Required secret {key} is not set")
        return value
