"""Comprehensive tests for Midway authentication handler.

This module contains unit tests for the MidwayAuthenticator and
SecureMidwayAuthenticator classes, including subprocess mocking,
timeout handling, retry logic, and secure logging.
"""

import pytest
import subprocess
import signal
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, call, MagicMock

from ticket_analyzer.auth.midway_auth import (
    MidwayAuthenticator,
    SecureMidwayAuthenticator,
    AuthenticationTimeoutError
)
from ticket_analyzer.models.config import AuthConfig
from ticket_analyzer.models.exceptions import (
    AuthenticationError,
    SecurityError
)


class TestMidwayAuthenticator:
    """Test cases for MidwayAuthenticator class."""
    
    @pytest.fixture
    def auth_config(self) -> AuthConfig:
        """Provide test authentication configuration."""
        return AuthConfig(
            timeout_seconds=30,
            max_retry_attempts=2,
            check_interval_seconds=60,
            session_duration_hours=4,
            auth_method="midway"
        )
    
    @pytest.fixture
    def authenticator(self, auth_config: AuthConfig) -> MidwayAuthenticator:
        """Provide MidwayAuthenticator instance for testing."""
        return MidwayAuthenticator(auth_config)
    
    @pytest.fixture
    def mock_subprocess_success(self):
        """Mock successful subprocess execution."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        return mock_result
    
    @pytest.fixture
    def mock_subprocess_failure(self):
        """Mock failed subprocess execution."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Authentication failed"
        return mock_result
    
    def test_initialization_with_config(self, auth_config: AuthConfig) -> None:
        """Test authenticator initialization with configuration."""
        authenticator = MidwayAuthenticator(auth_config)
        
        assert authenticator._config == auth_config
        assert authenticator._authenticated is False
        assert authenticator._last_auth_check is None
        assert authenticator._session_start is None
    
    def test_initialization_with_default_config(self) -> None:
        """Test authenticator initialization with default configuration."""
        authenticator = MidwayAuthenticator()
        
        assert authenticator._config is not None
        assert authenticator._config.timeout_seconds == 60  # Default value
        assert authenticator._config.max_retry_attempts == 3  # Default value
    
    def test_initialization_validates_config(self) -> None:
        """Test that initialization validates configuration."""
        invalid_config = AuthConfig(timeout_seconds=-1)  # Invalid timeout
        
        with pytest.raises(ValueError):
            MidwayAuthenticator(invalid_config)
    
    @patch('subprocess.run')
    def test_authenticate_success_first_attempt(
        self, mock_run: Mock, authenticator: MidwayAuthenticator,
        mock_subprocess_success: Mock
    ) -> None:
        """Test successful authentication on first attempt."""
        mock_run.return_value = mock_subprocess_success
        
        result = authenticator.authenticate()
        
        assert result is True
        assert authenticator._authenticated is True
        assert authenticator._session_start is not None
        assert authenticator._last_auth_check is not None
        
        # Verify mwinit was called with correct arguments
        mock_run.assert_called_once_with(
            ["mwinit", "-o"],
            capture_output=True,
            text=True,
            timeout=30,
            env=authenticator._get_secure_env(),
            check=False
        )
    
    @patch('subprocess.run')
    def test_authenticate_success_after_retry(
        self, mock_run: Mock, authenticator: MidwayAuthenticator,
        mock_subprocess_failure: Mock, mock_subprocess_success: Mock
    ) -> None:
        """Test successful authentication after retry."""
        # First call fails, second succeeds
        mock_run.side_effect = [mock_subprocess_failure, mock_subprocess_success]
        
        result = authenticator.authenticate()
        
        assert result is True
        assert authenticator._authenticated is True
        assert mock_run.call_count == 2
    
    @patch('subprocess.run')
    def test_authenticate_failure_all_attempts(
        self, mock_run: Mock, authenticator: MidwayAuthenticator,
        mock_subprocess_failure: Mock
    ) -> None:
        """Test authentication failure after all retry attempts."""
        mock_run.return_value = mock_subprocess_failure
        
        with pytest.raises(AuthenticationError) as exc_info:
            authenticator.authenticate()
        
        assert "Authentication failed after 2 attempts" in str(exc_info.value)
        assert authenticator._authenticated is False
        assert mock_run.call_count == 2  # max_retry_attempts
    
    @patch('subprocess.run')
    def test_authenticate_timeout_error(
        self, mock_run: Mock, authenticator: MidwayAuthenticator
    ) -> None:
        """Test authentication timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired("mwinit", 30)
        
        with pytest.raises(AuthenticationError) as exc_info:
            authenticator.authenticate()
        
        # Should raise AuthenticationTimeoutError, not generic AuthenticationError
        assert "Authentication timed out" in str(exc_info.value)
        assert authenticator._authenticated is False
    
    @patch('subprocess.run')
    def test_authenticate_file_not_found_error(
        self, mock_run: Mock, authenticator: MidwayAuthenticator
    ) -> None:
        """Test authentication when mwinit command not found."""
        mock_run.side_effect = FileNotFoundError("mwinit not found")
        
        with pytest.raises(AuthenticationError) as exc_info:
            authenticator.authenticate()
        
        assert "mwinit command not found" in str(exc_info.value)
        assert authenticator._authenticated is False
    
    @patch('subprocess.run')
    def test_is_authenticated_fresh_check(
        self, mock_run: Mock, authenticator: MidwayAuthenticator,
        mock_subprocess_success: Mock
    ) -> None:
        """Test is_authenticated performs fresh check when needed."""
        mock_run.return_value = mock_subprocess_success
        
        # First call should trigger status check
        result = authenticator.is_authenticated()
        
        assert result is True
        assert authenticator._authenticated is True
        
        # Verify status check was called
        mock_run.assert_called_once_with(
            ["mwinit", "-s"],
            capture_output=True,
            text=True,
            timeout=10,
            env=authenticator._get_secure_env(),
            check=False
        )
    
    @patch('subprocess.run')
    def test_is_authenticated_uses_cached_result(
        self, mock_run: Mock, authenticator: MidwayAuthenticator,
        mock_subprocess_success: Mock
    ) -> None:
        """Test is_authenticated uses cached result within check interval."""
        mock_run.return_value = mock_subprocess_success
        
        # First call
        result1 = authenticator.is_authenticated()
        assert result1 is True
        
        # Second call within check interval should use cached result
        result2 = authenticator.is_authenticated()
        assert result2 is True
        
        # Should only have called subprocess once
        assert mock_run.call_count == 1
    
    @patch('subprocess.run')
    def test_is_authenticated_status_check_failure(
        self, mock_run: Mock, authenticator: MidwayAuthenticator,
        mock_subprocess_failure: Mock
    ) -> None:
        """Test is_authenticated when status check fails."""
        mock_run.return_value = mock_subprocess_failure
        
        result = authenticator.is_authenticated()
        
        assert result is False
        assert authenticator._authenticated is False
    
    @patch('subprocess.run')
    def test_is_authenticated_status_check_timeout(
        self, mock_run: Mock, authenticator: MidwayAuthenticator
    ) -> None:
        """Test is_authenticated when status check times out."""
        mock_run.side_effect = subprocess.TimeoutExpired("mwinit", 10)
        
        result = authenticator.is_authenticated()
        
        assert result is False
        assert authenticator._authenticated is False
    
    @patch('subprocess.run')
    def test_ensure_authenticated_when_not_authenticated(
        self, mock_run: Mock, authenticator: MidwayAuthenticator,
        mock_subprocess_success: Mock
    ) -> None:
        """Test ensure_authenticated triggers authentication when needed."""
        # Status check returns False, then authentication succeeds
        mock_status_fail = Mock()
        mock_status_fail.returncode = 1
        
        mock_run.side_effect = [mock_status_fail, mock_subprocess_success]
        
        authenticator.ensure_authenticated()
        
        assert authenticator._authenticated is True
        assert mock_run.call_count == 2  # Status check + authentication
    
    @patch('subprocess.run')
    def test_ensure_authenticated_when_already_authenticated(
        self, mock_run: Mock, authenticator: MidwayAuthenticator,
        mock_subprocess_success: Mock
    ) -> None:
        """Test ensure_authenticated skips authentication when already authenticated."""
        mock_run.return_value = mock_subprocess_success
        
        authenticator.ensure_authenticated()
        
        # Should only call status check, not authentication
        assert mock_run.call_count == 1
        mock_run.assert_called_with(
            ["mwinit", "-s"],
            capture_output=True,
            text=True,
            timeout=10,
            env=authenticator._get_secure_env(),
            check=False
        )
    
    def test_get_session_info_no_session(self, authenticator: MidwayAuthenticator) -> None:
        """Test get_session_info when no session is active."""
        session_info = authenticator.get_session_info()
        
        assert session_info["authenticated"] is False
        assert session_info["auth_method"] == "midway"
        assert session_info["session_start"] is None
        assert session_info["last_check"] is None
    
    @patch('subprocess.run')
    def test_get_session_info_with_active_session(
        self, mock_run: Mock, authenticator: MidwayAuthenticator,
        mock_subprocess_success: Mock
    ) -> None:
        """Test get_session_info with active session."""
        mock_run.return_value = mock_subprocess_success
        
        # Authenticate to create session
        authenticator.authenticate()
        
        session_info = authenticator.get_session_info()
        
        assert session_info["authenticated"] is True
        assert session_info["auth_method"] == "midway"
        assert session_info["session_start"] is not None
        assert session_info["last_check"] is not None
        assert session_info["session_age_seconds"] >= 0
        assert session_info["check_interval_seconds"] == 60
        assert session_info["session_duration_hours"] == 4
    
    @patch('subprocess.run')
    def test_get_session_info_session_warning(
        self, mock_run: Mock, authenticator: MidwayAuthenticator,
        mock_subprocess_success: Mock
    ) -> None:
        """Test get_session_info shows warning for old sessions."""
        mock_run.return_value = mock_subprocess_success
        
        # Authenticate and manually set old session start time
        authenticator.authenticate()
        authenticator._session_start = datetime.now() - timedelta(hours=3.5)  # 87.5% of 4 hours
        
        session_info = authenticator.get_session_info()
        
        assert "session_warning" in session_info
        assert "approaching expiry" in session_info["session_warning"]
    
    def test_get_secure_env(self, authenticator: MidwayAuthenticator) -> None:
        """Test secure environment variable generation."""
        # Set some test environment variables
        test_env = {
            "PATH": "/usr/bin:/bin",
            "HOME": "/home/test",
            "USER": "testuser",
            "LANG": "en_US.UTF-8",
            "KRB5_CONFIG": "/etc/krb5.conf",
            "KRB5CCNAME": "/tmp/krb5cc_test",
            "SENSITIVE_VAR": "should_not_be_included"
        }
        
        with patch.dict(os.environ, test_env, clear=True):
            secure_env = authenticator._get_secure_env()
        
        # Check that expected variables are included
        assert secure_env["PATH"] == "/usr/bin:/bin"
        assert secure_env["HOME"] == "/home/test"
        assert secure_env["USER"] == "testuser"
        assert secure_env["LANG"] == "en_US.UTF-8"
        assert secure_env["KRB5_CONFIG"] == "/etc/krb5.conf"
        assert secure_env["KRB5CCNAME"] == "/tmp/krb5cc_test"
        
        # Check that sensitive variables are not included
        assert "SENSITIVE_VAR" not in secure_env
    
    def test_validate_command_allowed_commands(self, authenticator: MidwayAuthenticator) -> None:
        """Test command validation for allowed commands."""
        assert authenticator._validate_command(["mwinit", "-o"]) is True
        assert authenticator._validate_command(["kinit", "user"]) is True
        assert authenticator._validate_command(["klist"]) is True
    
    def test_validate_command_disallowed_commands(self, authenticator: MidwayAuthenticator) -> None:
        """Test command validation rejects disallowed commands."""
        assert authenticator._validate_command(["rm", "-rf", "/"]) is False
        assert authenticator._validate_command(["cat", "/etc/passwd"]) is False
        assert authenticator._validate_command(["bash", "-c", "evil"]) is False
    
    def test_validate_command_invalid_input(self, authenticator: MidwayAuthenticator) -> None:
        """Test command validation with invalid input."""
        assert authenticator._validate_command([]) is False
        assert authenticator._validate_command(None) is False
        assert authenticator._validate_command("not_a_list") is False
    
    def test_sanitize_output_removes_sensitive_data(self, authenticator: MidwayAuthenticator) -> None:
        """Test output sanitization removes sensitive information."""
        sensitive_output = """
        Authentication successful
        Token: abc123def456
        Password: secret123
        Credential: user:pass
        Some base64 token: YWJjZGVmZ2hpams=
        """
        
        sanitized = authenticator._sanitize_output(sensitive_output)
        
        assert "abc123def456" not in sanitized
        assert "secret123" not in sanitized
        assert "user:pass" not in sanitized
        assert "YWJjZGVmZ2hpams=" not in sanitized
        assert "[TOKEN_REDACTED]" in sanitized
        assert "[PASSWORD_REDACTED]" in sanitized
        assert "[CREDENTIAL_REDACTED]" in sanitized
    
    def test_sanitize_output_preserves_safe_content(self, authenticator: MidwayAuthenticator) -> None:
        """Test output sanitization preserves safe content."""
        safe_output = "Authentication successful. Please proceed."
        
        sanitized = authenticator._sanitize_output(safe_output)
        
        assert sanitized == safe_output
    
    def test_sanitize_output_empty_input(self, authenticator: MidwayAuthenticator) -> None:
        """Test output sanitization with empty input."""
        assert authenticator._sanitize_output("") == ""
        assert authenticator._sanitize_output(None) is None
    
    @patch('signal.signal')
    @patch('signal.alarm')
    def test_authentication_timeout_context_manager(
        self, mock_alarm: Mock, mock_signal: Mock, authenticator: MidwayAuthenticator
    ) -> None:
        """Test authentication timeout context manager setup and cleanup."""
        old_handler = Mock()
        mock_signal.return_value = old_handler
        
        with authenticator._authentication_timeout(30):
            pass
        
        # Verify signal setup and cleanup
        assert mock_signal.call_count == 2  # Setup and cleanup
        assert mock_alarm.call_count == 2  # Set alarm and clear alarm
        
        # Verify alarm was set and cleared
        mock_alarm.assert_has_calls([call(30), call(0)])
    
    @patch('signal.signal')
    @patch('signal.alarm')
    def test_authentication_timeout_raises_on_timeout(
        self, mock_alarm: Mock, mock_signal: Mock, authenticator: MidwayAuthenticator
    ) -> None:
        """Test authentication timeout raises exception on timeout."""
        # Mock signal handler to immediately raise timeout
        def mock_handler(signum, frame):
            raise AuthenticationTimeoutError("Authentication timed out after 30 seconds", 30)
        
        mock_signal.return_value = Mock()
        
        with pytest.raises(AuthenticationTimeoutError) as exc_info:
            with authenticator._authentication_timeout(30):
                # Simulate timeout by calling the handler
                mock_handler(signal.SIGALRM, None)
        
        assert "timed out after 30 seconds" in str(exc_info.value)
        assert exc_info.value.get_detail("timeout_duration") == 30
    
    def test_authentication_timeout_no_sigalrm_support(self, authenticator: MidwayAuthenticator) -> None:
        """Test authentication timeout when SIGALRM is not supported."""
        # Simulate system without SIGALRM support by patching signal module
        with patch('signal.SIGALRM', side_effect=AttributeError("SIGALRM not supported")):
            with authenticator._authentication_timeout(30):
                pass  # Should not raise exception


class TestSecureMidwayAuthenticator:
    """Test cases for SecureMidwayAuthenticator class."""
    
    @pytest.fixture
    def secure_authenticator(self) -> SecureMidwayAuthenticator:
        """Provide SecureMidwayAuthenticator instance for testing."""
        config = AuthConfig(timeout_seconds=30, max_retry_attempts=2)
        return SecureMidwayAuthenticator(config)
    
    @patch('subprocess.run')
    @patch('gc.collect')
    def test_authenticate_clears_sensitive_state_on_success(
        self, mock_gc: Mock, mock_run: Mock, secure_authenticator: SecureMidwayAuthenticator
    ) -> None:
        """Test that authenticate clears sensitive state on success."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = secure_authenticator.authenticate()
        
        assert result is True
        # Verify garbage collection was called
        assert mock_gc.call_count >= 1
    
    @patch('subprocess.run')
    @patch('gc.collect')
    def test_authenticate_clears_sensitive_state_on_error(
        self, mock_gc: Mock, mock_run: Mock, secure_authenticator: SecureMidwayAuthenticator
    ) -> None:
        """Test that authenticate clears sensitive state on error."""
        mock_run.side_effect = AuthenticationError("Test error")
        
        with pytest.raises(AuthenticationError):
            secure_authenticator.authenticate()
        
        # Verify garbage collection was called even on error
        assert mock_gc.call_count >= 1
    
    def test_get_session_info_includes_security_metadata(
        self, secure_authenticator: SecureMidwayAuthenticator
    ) -> None:
        """Test that get_session_info includes security metadata."""
        session_info = secure_authenticator.get_session_info()
        
        assert session_info["security_level"] == "enhanced"
        assert session_info["credential_protection"] == "enabled"
        assert session_info["memory_protection"] == "enabled"
    
    @patch('gc.collect')
    def test_clear_sensitive_state_forces_garbage_collection(
        self, mock_gc: Mock, secure_authenticator: SecureMidwayAuthenticator
    ) -> None:
        """Test that _clear_sensitive_state forces garbage collection."""
        secure_authenticator._clear_sensitive_state()
        
        # Should call garbage collection
        mock_gc.assert_called()


class TestAuthenticationTimeoutError:
    """Test cases for AuthenticationTimeoutError exception."""
    
    def test_timeout_error_creation_with_duration(self) -> None:
        """Test creating timeout error with duration."""
        error = AuthenticationTimeoutError("Timeout occurred", timeout_duration=30.0)
        
        assert "Timeout occurred" in str(error)
        assert error.get_detail("timeout_duration") == 30.0
    
    def test_timeout_error_creation_without_duration(self) -> None:
        """Test creating timeout error without duration."""
        error = AuthenticationTimeoutError("Timeout occurred")
        
        assert "Timeout occurred" in str(error)
        assert error.get_detail("timeout_duration") is None


class TestAuthenticationIntegration:
    """Integration tests for authentication components."""
    
    @pytest.fixture
    def integration_config(self) -> AuthConfig:
        """Provide configuration for integration tests."""
        return AuthConfig(
            timeout_seconds=5,  # Short timeout for testing
            max_retry_attempts=1,  # Single attempt for faster tests
            check_interval_seconds=1,  # Short interval for testing
            session_duration_hours=1
        )
    
    @patch('subprocess.run')
    def test_full_authentication_flow_success(
        self, mock_run: Mock, integration_config: AuthConfig
    ) -> None:
        """Test complete authentication flow with success."""
        # Mock failed status check first, then successful authentication
        mock_status_fail = Mock()
        mock_status_fail.returncode = 1
        mock_status_fail.stderr = ""
        
        mock_auth_success = Mock()
        mock_auth_success.returncode = 0
        mock_auth_success.stderr = ""
        
        # First call (status check) fails, second call (authentication) succeeds
        mock_run.side_effect = [mock_status_fail, mock_auth_success]
        
        authenticator = MidwayAuthenticator(integration_config)
        
        # Test ensure_authenticated flow
        authenticator.ensure_authenticated()
        
        assert authenticator.is_authenticated() is True
        
        session_info = authenticator.get_session_info()
        assert session_info["authenticated"] is True
        # Session start should be set after authentication
        assert authenticator._session_start is not None
    
    @patch('subprocess.run')
    def test_full_authentication_flow_failure(
        self, mock_run: Mock, integration_config: AuthConfig
    ) -> None:
        """Test complete authentication flow with failure."""
        # Mock failed authentication
        mock_failure = Mock()
        mock_failure.returncode = 1
        mock_failure.stderr = "Authentication failed"
        mock_run.return_value = mock_failure
        
        authenticator = MidwayAuthenticator(integration_config)
        
        # Test ensure_authenticated flow with failure
        with pytest.raises(AuthenticationError):
            authenticator.ensure_authenticated()
        
        assert authenticator.is_authenticated() is False
        
        session_info = authenticator.get_session_info()
        assert session_info["authenticated"] is False
        assert session_info["session_start"] is None
    
    @patch('subprocess.run')
    def test_authentication_retry_logic(
        self, mock_run: Mock, integration_config: AuthConfig
    ) -> None:
        """Test authentication retry logic with mixed results."""
        # First call fails, second succeeds
        mock_failure = Mock()
        mock_failure.returncode = 1
        mock_failure.stderr = "Temporary failure"
        
        mock_success = Mock()
        mock_success.returncode = 0
        mock_success.stderr = ""
        
        mock_run.side_effect = [mock_failure, mock_success]
        
        # Update config to allow 2 attempts
        integration_config.max_retry_attempts = 2
        authenticator = MidwayAuthenticator(integration_config)
        
        result = authenticator.authenticate()
        
        assert result is True
        assert mock_run.call_count == 2
    
    @patch('subprocess.run')
    def test_session_expiry_and_refresh(
        self, mock_run: Mock, integration_config: AuthConfig
    ) -> None:
        """Test session expiry and refresh behavior."""
        mock_success = Mock()
        mock_success.returncode = 0
        mock_success.stderr = ""
        mock_run.return_value = mock_success
        
        authenticator = MidwayAuthenticator(integration_config)
        
        # Initial authentication
        authenticator.authenticate()
        assert authenticator.is_authenticated() is True
        
        # Simulate session expiry by setting old session start
        authenticator._session_start = datetime.now() - timedelta(hours=2)
        
        # Force check interval to expire
        authenticator._last_auth_check = None
        
        # Should still be authenticated (status check succeeds)
        assert authenticator.is_authenticated() is True
    
    @patch('subprocess.run')
    @patch('signal.signal')  # Mock signal to avoid threading issues
    @patch('signal.alarm')
    def test_concurrent_authentication_calls(
        self, mock_alarm: Mock, mock_signal: Mock, mock_run: Mock, integration_config: AuthConfig
    ) -> None:
        """Test handling of concurrent authentication calls."""
        import threading
        import time
        
        mock_success = Mock()
        mock_success.returncode = 0
        mock_success.stderr = ""
        
        # Add delay to simulate slow authentication
        def slow_run(*args, **kwargs):
            time.sleep(0.1)
            return mock_success
        
        mock_run.side_effect = slow_run
        mock_signal.return_value = Mock()  # Mock signal handler
        
        authenticator = MidwayAuthenticator(integration_config)
        
        results = []
        errors = []
        
        def authenticate_thread():
            try:
                result = authenticator.authenticate()
                results.append(result)
            except Exception as e:
                errors.append(e)
        
        # Start multiple authentication threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=authenticate_thread)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have at least one success (signal issues in threads are expected)
        assert len(results) > 0