"""Comprehensive tests for SecretsManager credential loading.

Tests verify:
- All getter methods return correct values
- Environment variable priority over file fallback
- File fallback works when env var missing
- require() raises ValueError for missing secrets
- Secrets are never logged in plaintext
"""

import os
import logging
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from config.secrets_manager import SecretsManager


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_project_root(tmp_path: Path) -> Path:
    """Create a temporary project root for testing file-based secrets."""
    return tmp_path


@pytest.fixture
def secrets_manager(temp_project_root: Path) -> SecretsManager:
    """Create a SecretsManager instance with temporary project root."""
    return SecretsManager(project_root=temp_project_root)


@pytest.fixture
def env_cleanup():
    """Clean up DHAN_* environment variables before and after tests."""
    dhan_vars = [
        "DHAN_CLIENT_ID", "DHAN_ACCESS_TOKEN", "DHAN_TOTP_SECRET",
        "DHAN_PIN", "DHAN_AUTH_MODE", "DHAN_ENVIRONMENT",
        "DHAN_CLIENT_ID_FILE", "DHAN_ACCESS_TOKEN_FILE",
        "DHAN_TOTP_SECRET_FILE", "DHAN_PIN_FILE"
    ]
    
    # Store original values
    original_values = {}
    for var in dhan_vars:
        original_values[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]
    
    yield
    
    # Restore original values
    for var, value in original_values.items():
        if value is not None:
            os.environ[var] = value
        elif var in os.environ:
            del os.environ[var]


# ============================================================================
# TEST 1: Client ID Loading
# ============================================================================

class TestClientIDLoading:
    """Verify Dhan client ID loading from env and file."""

    def test_client_id_from_env(self, secrets_manager: SecretsManager, env_cleanup):
        """Client ID should be loaded from DHAN_CLIENT_ID env var."""
        os.environ["DHAN_CLIENT_ID"] = "test_client_123"
        assert secrets_manager.get_dhan_client_id() == "test_client_123"

    def test_client_id_from_file(self, secrets_manager: SecretsManager, env_cleanup, temp_project_root: Path):
        """Client ID should fallback to file when env var missing."""
        config_dir = temp_project_root / "config"
        config_dir.mkdir()
        (config_dir / "dhan-client-id.txt").write_text("file_client_456")
        
        assert secrets_manager.get_dhan_client_id() == "file_client_456"

    def test_client_id_env_priority_over_file(self, secrets_manager: SecretsManager, env_cleanup, temp_project_root: Path):
        """Env var should take priority over file."""
        os.environ["DHAN_CLIENT_ID"] = "env_client_789"
        
        config_dir = temp_project_root / "config"
        config_dir.mkdir()
        (config_dir / "dhan-client-id.txt").write_text("file_client_000")
        
        assert secrets_manager.get_dhan_client_id() == "env_client_789"

    def test_client_id_empty_when_missing(self, secrets_manager: SecretsManager, env_cleanup):
        """Client ID should return empty string when neither env nor file exists."""
        assert secrets_manager.get_dhan_client_id() == ""


# ============================================================================
# TEST 2: Access Token Loading
# ============================================================================

class TestAccessTokenLoading:
    """Verify Dhan access token loading from env and file."""

    def test_access_token_from_env(self, secrets_manager: SecretsManager, env_cleanup):
        """Access token should be loaded from DHAN_ACCESS_TOKEN env var."""
        os.environ["DHAN_ACCESS_TOKEN"] = "token_abc123"
        assert secrets_manager.get_dhan_access_token() == "token_abc123"

    def test_access_token_from_file(self, secrets_manager: SecretsManager, env_cleanup, temp_project_root: Path):
        """Access token should fallback to file when env var missing."""
        config_dir = temp_project_root / "config"
        config_dir.mkdir()
        (config_dir / "dhan-access-token.txt").write_text("token_file_xyz")
        
        assert secrets_manager.get_dhan_access_token() == "token_file_xyz"

    def test_access_token_env_priority_over_file(self, secrets_manager: SecretsManager, env_cleanup, temp_project_root: Path):
        """Env var should take priority over file."""
        os.environ["DHAN_ACCESS_TOKEN"] = "token_env_priority"
        
        config_dir = temp_project_root / "config"
        config_dir.mkdir()
        (config_dir / "dhan-access-token.txt").write_text("token_file_low")
        
        assert secrets_manager.get_dhan_access_token() == "token_env_priority"

    def test_access_token_empty_when_missing(self, secrets_manager: SecretsManager, env_cleanup):
        """Access token should return empty string when neither env nor file exists."""
        assert secrets_manager.get_dhan_access_token() == ""


# ============================================================================
# TEST 3: TOTP Secret Loading
# ============================================================================

class TestTOTPSecretLoading:
    """Verify TOTP secret loading with None fallback."""

    def test_totp_from_env(self, secrets_manager: SecretsManager, env_cleanup):
        """TOTP secret should be loaded from DHAN_TOTP_SECRET env var."""
        os.environ["DHAN_TOTP_SECRET"] = "JBSWY3DPEHPK3PXP"
        result = secrets_manager.get_dhan_totp_secret()
        assert result == "JBSWY3DPEHPK3PXP"

    def test_totp_from_file(self, secrets_manager: SecretsManager, env_cleanup, temp_project_root: Path):
        """TOTP secret should fallback to file when env var missing."""
        config_dir = temp_project_root / "config"
        config_dir.mkdir()
        (config_dir / "dhan-totp-secret.txt").write_text("TOTP_FILE_SECRET123")
        
        result = secrets_manager.get_dhan_totp_secret()
        assert result == "TOTP_FILE_SECRET123"

    def test_totp_returns_none_when_missing(self, secrets_manager: SecretsManager, env_cleanup):
        """TOTP secret should return None when neither env nor file exists."""
        result = secrets_manager.get_dhan_totp_secret()
        assert result is None

    def test_totp_env_priority_over_file(self, secrets_manager: SecretsManager, env_cleanup, temp_project_root: Path):
        """Env var should take priority over file."""
        os.environ["DHAN_TOTP_SECRET"] = "TOTP_ENV_PRIORITY"
        
        config_dir = temp_project_root / "config"
        config_dir.mkdir()
        (config_dir / "dhan-totp-secret.txt").write_text("TOTP_FILE_LOW")
        
        assert secrets_manager.get_dhan_totp_secret() == "TOTP_ENV_PRIORITY"


# ============================================================================
# TEST 4: PIN Loading
# ============================================================================

class TestPINLoading:
    """Verify PIN loading with None fallback."""

    def test_pin_from_env(self, secrets_manager: SecretsManager, env_cleanup):
        """PIN should be loaded from DHAN_PIN env var."""
        os.environ["DHAN_PIN"] = "123456"
        result = secrets_manager.get_dhan_pin()
        assert result == "123456"

    def test_pin_from_file(self, secrets_manager: SecretsManager, env_cleanup, temp_project_root: Path):
        """PIN should fallback to file when env var missing."""
        config_dir = temp_project_root / "config"
        config_dir.mkdir()
        (config_dir / "dhan-pin.txt").write_text("654321")
        
        result = secrets_manager.get_dhan_pin()
        assert result == "654321"

    def test_pin_returns_none_when_missing(self, secrets_manager: SecretsManager, env_cleanup):
        """PIN should return None when neither env nor file exists."""
        result = secrets_manager.get_dhan_pin()
        assert result is None

    def test_pin_env_priority_over_file(self, secrets_manager: SecretsManager, env_cleanup, temp_project_root: Path):
        """Env var should take priority over file."""
        os.environ["DHAN_PIN"] = "999999"
        
        config_dir = temp_project_root / "config"
        config_dir.mkdir()
        (config_dir / "dhan-pin.txt").write_text("000000")
        
        assert secrets_manager.get_dhan_pin() == "999999"


# ============================================================================
# TEST 5: Auth Mode and Environment
# ============================================================================

class TestAuthModeAndEnvironment:
    """Verify auth mode and environment configuration."""

    def test_auth_mode_from_env(self, secrets_manager: SecretsManager, env_cleanup):
        """Auth mode should be loaded from DHAN_AUTH_MODE env var."""
        os.environ["DHAN_AUTH_MODE"] = "TOTP_GENERATED"
        assert secrets_manager.get_dhan_auth_mode() == "TOTP_GENERATED"

    def test_auth_mode_default_static(self, secrets_manager: SecretsManager, env_cleanup):
        """Auth mode should default to STATIC when not set."""
        assert secrets_manager.get_dhan_auth_mode() == "STATIC"

    def test_environment_from_env(self, secrets_manager: SecretsManager, env_cleanup):
        """Environment should be loaded from DHAN_ENVIRONMENT env var."""
        os.environ["DHAN_ENVIRONMENT"] = "SANDBOX"
        assert secrets_manager.get_dhan_environment() == "SANDBOX"

    def test_environment_default_live(self, secrets_manager: SecretsManager, env_cleanup):
        """Environment should default to LIVE when not set."""
        assert secrets_manager.get_dhan_environment() == "LIVE"


# ============================================================================
# TEST 6: require() Method
# ============================================================================

class TestRequireMethod:
    """Verify require() raises ValueError for missing secrets."""

    def test_require_returns_value_when_present(self, secrets_manager: SecretsManager, env_cleanup):
        """require() should return value when env var is set."""
        os.environ["TEST_SECRET"] = "secret_value"
        assert secrets_manager.require("TEST_SECRET") == "secret_value"

    def test_require_raises_for_missing(self, secrets_manager: SecretsManager, env_cleanup):
        """require() should raise ValueError when secret is missing."""
        with pytest.raises(ValueError, match="Required secret MISSING_KEY is not set"):
            secrets_manager.require("MISSING_KEY")

    def test_require_raises_for_empty(self, secrets_manager: SecretsManager, env_cleanup):
        """require() should raise ValueError when secret is empty string."""
        os.environ["EMPTY_SECRET"] = ""
        with pytest.raises(ValueError, match="Required secret EMPTY_SECRET is not set"):
            secrets_manager.require("EMPTY_SECRET")


# ============================================================================
# TEST 7: Secrets Never Logged
# ============================================================================

class TestSecretsNotLogged:
    """Verify secrets are never logged in plaintext."""

    def test_get_methods_do_not_log_secrets(
        self, 
        secrets_manager: SecretsManager, 
        env_cleanup,
        caplog
    ):
        """Getter methods should not log secret values."""
        os.environ["DHAN_CLIENT_ID"] = "secret_client_id"
        os.environ["DHAN_ACCESS_TOKEN"] = "secret_token_123"
        os.environ["DHAN_TOTP_SECRET"] = "secret_totp"
        os.environ["DHAN_PIN"] = "secret_pin"
        
        with caplog.at_level(logging.DEBUG):
            _ = secrets_manager.get_dhan_client_id()
            _ = secrets_manager.get_dhan_access_token()
            _ = secrets_manager.get_dhan_totp_secret()
            _ = secrets_manager.get_dhan_pin()
        
        # Verify no secret values appear in logs
        for record in caplog.records:
            assert "secret_client_id" not in record.message
            assert "secret_token_123" not in record.message
            assert "secret_totp" not in record.message
            assert "secret_pin" not in record.message

    def test_require_does_not_log_secret_value(
        self,
        secrets_manager: SecretsManager,
        env_cleanup,
        caplog
    ):
        """require() error message should not log the secret value."""
        os.environ["SENSITIVE_KEY"] = "super_secret_value"
        
        with caplog.at_level(logging.ERROR):
            # Should not raise since value exists
            result = secrets_manager.require("SENSITIVE_KEY")
            assert result == "super_secret_value"
        
        # Verify secret value not in logs
        for record in caplog.records:
            assert "super_secret_value" not in record.message


# ============================================================================
# TEST 8: Custom File Path Support
# ============================================================================

class TestCustomFilePaths:
    """Verify custom file path configuration via env vars."""

    def test_custom_client_id_file_path(
        self, 
        secrets_manager: SecretsManager, 
        env_cleanup,
        temp_project_root: Path
    ):
        """Should use custom file path from DHAN_CLIENT_ID_FILE env var."""
        custom_dir = temp_project_root / "custom"
        custom_dir.mkdir()
        (custom_dir / "my-client-id.txt").write_text("custom_client_123")
        
        os.environ["DHAN_CLIENT_ID_FILE"] = "custom/my-client-id.txt"
        
        assert secrets_manager.get_dhan_client_id() == "custom_client_123"

    def test_custom_token_file_path(
        self,
        secrets_manager: SecretsManager,
        env_cleanup,
        temp_project_root: Path
    ):
        """Should use custom file path from DHAN_ACCESS_TOKEN_FILE env var."""
        custom_dir = temp_project_root / "secrets"
        custom_dir.mkdir()
        (custom_dir / "token.txt").write_text("custom_token_xyz")
        
        os.environ["DHAN_ACCESS_TOKEN_FILE"] = "secrets/token.txt"
        
        assert secrets_manager.get_dhan_access_token() == "custom_token_xyz"


# ============================================================================
# TEST 9: File Content Stripping
# ============================================================================

class TestFileContentHandling:
    """Verify file content is properly stripped of whitespace."""

    def test_file_content_stripped(self, secrets_manager: SecretsManager, env_cleanup, temp_project_root: Path):
        """File content should be stripped of leading/trailing whitespace."""
        config_dir = temp_project_root / "config"
        config_dir.mkdir()
        (config_dir / "dhan-client-id.txt").write_text("  client_with_spaces  \n")
        
        assert secrets_manager.get_dhan_client_id() == "client_with_spaces"

    def test_file_with_newlines(self, secrets_manager: SecretsManager, env_cleanup, temp_project_root: Path):
        """File with newlines should return clean value."""
        config_dir = temp_project_root / "config"
        config_dir.mkdir()
        (config_dir / "dhan-access-token.txt").write_text("\ntoken_value\n\n")
        
        assert secrets_manager.get_dhan_access_token() == "token_value"


# ============================================================================
# TEST 10: Integration with main.py pattern
# ============================================================================

class TestIntegrationPattern:
    """Verify SecretsManager works as expected in main.py usage pattern."""

    def test_secrets_manager_instantiation(self):
        """SecretsManager should instantiate without arguments."""
        secrets = SecretsManager()
        assert secrets is not None

    def test_secrets_manager_with_project_root(self, temp_project_root: Path):
        """SecretsManager should accept custom project root."""
        secrets = SecretsManager(project_root=temp_project_root)
        assert secrets._root == temp_project_root

    def test_main_py_usage_pattern(self, env_cleanup):
        """Verify the exact usage pattern from main.py works."""
        os.environ["DHAN_CLIENT_ID"] = "main_client"
        os.environ["DHAN_ACCESS_TOKEN"] = "main_token"
        
        # This is the exact pattern used in main.py
        secrets = SecretsManager()
        client_id = secrets.get_dhan_client_id()
        access_token = secrets.get_dhan_access_token()
        
        assert client_id == "main_client"
        assert access_token == "main_token"
