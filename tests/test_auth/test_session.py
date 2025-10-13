"""Comprehensive tests for authentication session management.

This module contains unit tests for the AuthenticationSession and
SecureAuthenticationSession classes, covering session lifecycle,
expiry handling, metadata management, and secure cleanup.
"""

import pytest
import gc
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
from unittest.mock import Mock, patch, call

from ticket_analyzer.auth.session import (
    AuthenticationSession,
    SecureAuthenticationSession,
    SessionMetadata
)
from ticket_analyzer.models.config import AuthConfig
from ticket_analyzer.models.exceptions import AuthenticationError, SecurityError


class TestSessionMetadata:
    """Test cases for SessionMetadata dataclass."""
    
    @pytest.fixture
    def sample_metadata(self) -> SessionMetadata:
        """Provide sample session metadata for testing."""
        now = datetime.now()
        return SessionMetadata(
            session_id="test_session_123",
            start_time=now,
            last_activity=now,
            expiry_time=now + timedelta(hours=8),
            auth_method="midway",
            user_info={"username": "testuser"},
            security_level="standard",
            refresh_count=0
        )
    
    def test_metadata_creation(self, sample_metadata: SessionMetadata) -> None:
        """Test session metadata creation with all fields."""
        assert sample_metadata.session_id == "test_session_123"
        assert sample_metadata.auth_method == "midway"
        assert sample_metadata.security_level == "standard"
        assert sample_metadata.refresh_count == 0
        assert sample_metadata.user_info == {"username": "testuser"}
    
    def test_is_expired_false_for_valid_session(self, sample_metadata: SessionMetadata) -> None:
        """Test is_expired returns False for valid session."""
        # Session expires in the future
        sample_metadata.expiry_time = datetime.now() + timedelta(hours=1)
        
        assert sample_metadata.is_expired() is False
    
    def test_is_expired_true_for_expired_session(self, sample_metadata: SessionMetadata) -> None:
        """Test is_expired returns True for expired session."""
        # Session expired 1 hour ago
        sample_metadata.expiry_time = datetime.now() - timedelta(hours=1)
        
        assert sample_metadata.is_expired() is True
    
    def test_time_until_expiry_positive_for_valid_session(self, sample_metadata: SessionMetadata) -> None:
        """Test time_until_expiry returns positive value for valid session."""
        # Session expires in 2 hours
        sample_metadata.expiry_time = datetime.now() + timedelta(hours=2)
        
        time_remaining = sample_metadata.time_until_expiry()
        
        assert time_remaining.total_seconds() > 0
        assert time_remaining.total_seconds() <= 2 * 3600  # Less than or equal to 2 hours
    
    def test_time_until_expiry_negative_for_expired_session(self, sample_metadata: SessionMetadata) -> None:
        """Test time_until_expiry returns negative value for expired session."""
        # Session expired 1 hour ago
        sample_metadata.expiry_time = datetime.now() - timedelta(hours=1)
        
        time_remaining = sample_metadata.time_until_expiry()
        
        assert time_remaining.total_seconds() < 0
    
    def test_update_activity(self, sample_metadata: SessionMetadata) -> None:
        """Test update_activity updates last_activity timestamp."""
        original_activity = sample_metadata.last_activity
        
        # Wait a small amount to ensure timestamp difference
        time.sleep(0.01)
        sample_metadata.update_activity()
        
        assert sample_metadata.last_activity > original_activity
    
    def test_to_dict_conversion(self, sample_metadata: SessionMetadata) -> None:
        """Test conversion to dictionary representation."""
        result = sample_metadata.to_dict()
        
        expected_keys = {
            "session_id", "start_time", "last_activity", "expiry_time",
            "auth_method", "user_info", "security_level", "refresh_count",
            "is_expired", "time_until_expiry_seconds"
        }
        
        assert set(result.keys()) == expected_keys
        assert result["session_id"] == "test_session_123"
        assert result["auth_method"] == "midway"
        assert result["security_level"] == "standard"
        assert result["refresh_count"] == 0
        assert isinstance(result["is_expired"], bool)
        assert isinstance(result["time_until_expiry_seconds"], int)


class TestAuthenticationSession:
    """Test cases for AuthenticationSession class."""
    
    @pytest.fixture
    def session_config(self) -> AuthConfig:
        """Provide test session configuration."""
        return AuthConfig(
            session_duration_hours=2,
            check_interval_seconds=60,
            auth_method="midway",
            auto_refresh=True
        )
    
    @pytest.fixture
    def auth_session(self, session_config: AuthConfig) -> AuthenticationSession:
        """Provide AuthenticationSession instance for testing."""
        return AuthenticationSession(session_config)
    
    def test_initialization_with_config(self, session_config: AuthConfig) -> None:
        """Test session initialization with configuration."""
        session = AuthenticationSession(session_config)
        
        assert session._config == session_config
        assert session._metadata is None
        assert session._lock is not None
        assert session._cleanup_callbacks == []
    
    def test_initialization_with_default_config(self) -> None:
        """Test session initialization with default configuration."""
        session = AuthenticationSession()
        
        assert session._config is not None
        assert session._config.session_duration_hours == 8  # Default value
    
    def test_start_session_creates_metadata(self, auth_session: AuthenticationSession) -> None:
        """Test start_session creates session metadata."""
        auth_session.start_session()
        
        assert auth_session._metadata is not None
        assert auth_session._metadata.session_id is not None
        assert auth_session._metadata.start_time is not None
        assert auth_session._metadata.last_activity is not None
        assert auth_session._metadata.expiry_time is not None
        assert auth_session._metadata.auth_method == "midway"
    
    def test_start_session_sets_correct_expiry(self, auth_session: AuthenticationSession) -> None:
        """Test start_session sets correct expiry time."""
        start_time = datetime.now()
        auth_session.start_session()
        
        expected_expiry = start_time + timedelta(hours=2)
        actual_expiry = auth_session._metadata.expiry_time
        
        # Allow 1 second tolerance for test execution time
        assert abs((actual_expiry - expected_expiry).total_seconds()) < 1
    
    def test_start_session_cleans_up_existing_session(self, auth_session: AuthenticationSession) -> None:
        """Test start_session cleans up existing session before creating new one."""
        # Start first session
        auth_session.start_session()
        first_session_id = auth_session._metadata.session_id
        
        # Start second session
        auth_session.start_session()
        second_session_id = auth_session._metadata.session_id
        
        assert first_session_id != second_session_id
    
    def test_start_session_handles_errors(self, auth_session: AuthenticationSession) -> None:
        """Test start_session handles errors gracefully."""
        # Mock _generate_session_id to raise an exception
        with patch.object(auth_session, '_generate_session_id', side_effect=Exception("Test error")):
            with pytest.raises(AuthenticationError) as exc_info:
                auth_session.start_session()
            
            assert "Failed to start authentication session" in str(exc_info.value)
    
    def test_end_session_cleans_up_metadata(self, auth_session: AuthenticationSession) -> None:
        """Test end_session cleans up session metadata."""
        auth_session.start_session()
        assert auth_session._metadata is not None
        
        auth_session.end_session()
        assert auth_session._metadata is None
    
    def test_end_session_executes_cleanup_callbacks(self, auth_session: AuthenticationSession) -> None:
        """Test end_session executes cleanup callbacks."""
        callback_mock = Mock()
        auth_session.add_cleanup_callback(callback_mock)
        
        auth_session.start_session()
        auth_session.end_session()
        
        callback_mock.assert_called_once()
    
    def test_end_session_handles_callback_errors(self, auth_session: AuthenticationSession) -> None:
        """Test end_session handles callback errors gracefully."""
        error_callback = Mock(side_effect=Exception("Callback error"))
        success_callback = Mock()
        
        auth_session.add_cleanup_callback(error_callback)
        auth_session.add_cleanup_callback(success_callback)
        
        auth_session.start_session()
        auth_session.end_session()  # Should not raise exception
        
        # Both callbacks should have been called
        error_callback.assert_called_once()
        success_callback.assert_called_once()
    
    def test_end_session_no_active_session(self, auth_session: AuthenticationSession) -> None:
        """Test end_session when no active session exists."""
        # Should not raise exception
        auth_session.end_session()
        assert auth_session._metadata is None
    
    def test_is_session_valid_no_session(self, auth_session: AuthenticationSession) -> None:
        """Test is_session_valid returns False when no session exists."""
        assert auth_session.is_session_valid() is False
    
    def test_is_session_valid_active_session(self, auth_session: AuthenticationSession) -> None:
        """Test is_session_valid returns True for active session."""
        auth_session.start_session()
        
        assert auth_session.is_session_valid() is True
    
    def test_is_session_valid_expired_session(self, auth_session: AuthenticationSession) -> None:
        """Test is_session_valid returns False for expired session."""
        auth_session.start_session()
        
        # Manually expire the session
        auth_session._metadata.expiry_time = datetime.now() - timedelta(hours=1)
        
        assert auth_session.is_session_valid() is False
        assert auth_session._metadata is None  # Should be cleaned up
    
    def test_is_session_valid_updates_activity(self, auth_session: AuthenticationSession) -> None:
        """Test is_session_valid updates last activity timestamp."""
        auth_session.start_session()
        original_activity = auth_session._metadata.last_activity
        
        time.sleep(0.01)  # Small delay
        auth_session.is_session_valid()
        
        assert auth_session._metadata.last_activity > original_activity
    
    def test_get_session_duration_no_session(self, auth_session: AuthenticationSession) -> None:
        """Test get_session_duration returns None when no session exists."""
        assert auth_session.get_session_duration() is None
    
    def test_get_session_duration_active_session(self, auth_session: AuthenticationSession) -> None:
        """Test get_session_duration returns start time for active session."""
        auth_session.start_session()
        start_time = auth_session._metadata.start_time
        
        duration = auth_session.get_session_duration()
        
        assert duration == start_time
    
    def test_refresh_session_no_session(self, auth_session: AuthenticationSession) -> None:
        """Test refresh_session returns False when no session exists."""
        result = auth_session.refresh_session()
        
        assert result is False
    
    def test_refresh_session_expired_session(self, auth_session: AuthenticationSession) -> None:
        """Test refresh_session returns False for expired session."""
        auth_session.start_session()
        
        # Manually expire the session
        auth_session._metadata.expiry_time = datetime.now() - timedelta(hours=1)
        
        result = auth_session.refresh_session()
        
        assert result is False
        assert auth_session._metadata is None  # Should be cleaned up
    
    def test_refresh_session_valid_session(self, auth_session: AuthenticationSession) -> None:
        """Test refresh_session extends expiry for valid session."""
        auth_session.start_session()
        original_expiry = auth_session._metadata.expiry_time
        original_refresh_count = auth_session._metadata.refresh_count
        
        result = auth_session.refresh_session()
        
        assert result is True
        assert auth_session._metadata.expiry_time > original_expiry
        assert auth_session._metadata.refresh_count == original_refresh_count + 1
    
    def test_refresh_session_handles_errors(self, auth_session: AuthenticationSession) -> None:
        """Test refresh_session handles errors gracefully."""
        auth_session.start_session()
        
        # Mock timedelta to raise an exception during refresh
        with patch('ticket_analyzer.auth.session.timedelta') as mock_timedelta:
            mock_timedelta.side_effect = Exception("Time error")
            
            with pytest.raises(AuthenticationError) as exc_info:
                auth_session.refresh_session()
            
            assert "Failed to refresh session" in str(exc_info.value)
    
    def test_get_session_metadata_no_session(self, auth_session: AuthenticationSession) -> None:
        """Test get_session_metadata when no session exists."""
        metadata = auth_session.get_session_metadata()
        
        assert metadata["active"] is False
        assert "No active session" in metadata["message"]
    
    def test_get_session_metadata_active_session(self, auth_session: AuthenticationSession) -> None:
        """Test get_session_metadata for active session."""
        auth_session.start_session()
        
        metadata = auth_session.get_session_metadata()
        
        assert metadata["active"] is True
        assert metadata["session_id"] is not None
        assert metadata["auth_method"] == "midway"
        assert "config" in metadata
        assert metadata["config"]["session_duration_hours"] == 2
    
    def test_add_cleanup_callback(self, auth_session: AuthenticationSession) -> None:
        """Test adding cleanup callbacks."""
        callback1 = Mock()
        callback2 = Mock()
        
        auth_session.add_cleanup_callback(callback1)
        auth_session.add_cleanup_callback(callback2)
        
        assert len(auth_session._cleanup_callbacks) == 2
        assert callback1 in auth_session._cleanup_callbacks
        assert callback2 in auth_session._cleanup_callbacks
    
    def test_remove_cleanup_callback(self, auth_session: AuthenticationSession) -> None:
        """Test removing cleanup callbacks."""
        callback1 = Mock()
        callback2 = Mock()
        
        auth_session.add_cleanup_callback(callback1)
        auth_session.add_cleanup_callback(callback2)
        
        auth_session.remove_cleanup_callback(callback1)
        
        assert len(auth_session._cleanup_callbacks) == 1
        assert callback1 not in auth_session._cleanup_callbacks
        assert callback2 in auth_session._cleanup_callbacks
    
    def test_remove_cleanup_callback_not_exists(self, auth_session: AuthenticationSession) -> None:
        """Test removing non-existent cleanup callback."""
        callback = Mock()
        
        # Should not raise exception
        auth_session.remove_cleanup_callback(callback)
        assert len(auth_session._cleanup_callbacks) == 0
    
    def test_get_time_until_expiry_no_session(self, auth_session: AuthenticationSession) -> None:
        """Test get_time_until_expiry returns None when no session exists."""
        assert auth_session.get_time_until_expiry() is None
    
    def test_get_time_until_expiry_active_session(self, auth_session: AuthenticationSession) -> None:
        """Test get_time_until_expiry returns correct time for active session."""
        auth_session.start_session()
        
        time_remaining = auth_session.get_time_until_expiry()
        
        assert time_remaining is not None
        assert time_remaining.total_seconds() > 0
        # Should be close to 2 hours (session duration)
        assert time_remaining.total_seconds() <= 2 * 3600
    
    def test_get_time_until_expiry_expired_session(self, auth_session: AuthenticationSession) -> None:
        """Test get_time_until_expiry returns None for expired session."""
        auth_session.start_session()
        
        # Manually expire the session
        auth_session._metadata.expiry_time = datetime.now() - timedelta(hours=1)
        
        assert auth_session.get_time_until_expiry() is None
    
    def test_is_near_expiry_no_session(self, auth_session: AuthenticationSession) -> None:
        """Test is_near_expiry returns False when no session exists."""
        assert auth_session.is_near_expiry() is False
    
    def test_is_near_expiry_not_near(self, auth_session: AuthenticationSession) -> None:
        """Test is_near_expiry returns False when session is not near expiry."""
        auth_session.start_session()
        
        # Session expires in 2 hours, default threshold is 15 minutes
        assert auth_session.is_near_expiry() is False
    
    def test_is_near_expiry_near_expiry(self, auth_session: AuthenticationSession) -> None:
        """Test is_near_expiry returns True when session is near expiry."""
        auth_session.start_session()
        
        # Set expiry to 10 minutes from now
        auth_session._metadata.expiry_time = datetime.now() + timedelta(minutes=10)
        
        assert auth_session.is_near_expiry() is True
    
    def test_is_near_expiry_custom_threshold(self, auth_session: AuthenticationSession) -> None:
        """Test is_near_expiry with custom threshold."""
        auth_session.start_session()
        
        # Set expiry to 30 minutes from now
        auth_session._metadata.expiry_time = datetime.now() + timedelta(minutes=30)
        
        # Should not be near expiry with 15-minute threshold
        assert auth_session.is_near_expiry(threshold_minutes=15) is False
        
        # Should be near expiry with 45-minute threshold
        assert auth_session.is_near_expiry(threshold_minutes=45) is True
    
    def test_generate_session_id_uniqueness(self, auth_session: AuthenticationSession) -> None:
        """Test session ID generation produces unique IDs."""
        id1 = auth_session._generate_session_id()
        id2 = auth_session._generate_session_id()
        
        assert id1 != id2
        assert id1.startswith("auth_session_")
        assert id2.startswith("auth_session_")
        assert len(id1) > len("auth_session_")
        assert len(id2) > len("auth_session_")
    
    @patch('gc.collect')
    def test_cleanup_session_data_forces_garbage_collection(
        self, mock_gc: Mock, auth_session: AuthenticationSession
    ) -> None:
        """Test _cleanup_session_data forces garbage collection."""
        auth_session.start_session()
        
        auth_session._cleanup_session_data()
        
        mock_gc.assert_called()
        assert auth_session._metadata is None
    
    def test_context_manager_entry_and_exit(self, auth_session: AuthenticationSession) -> None:
        """Test context manager entry and exit behavior."""
        with auth_session as session:
            assert session is auth_session
        
        # Session should be ended after exiting context
        assert auth_session._metadata is None
    
    def test_context_manager_with_exception(self, auth_session: AuthenticationSession) -> None:
        """Test context manager properly cleans up on exception."""
        auth_session.start_session()
        
        try:
            with auth_session:
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Session should still be cleaned up
        assert auth_session._metadata is None


class TestSecureAuthenticationSession:
    """Test cases for SecureAuthenticationSession class."""
    
    @pytest.fixture
    def secure_session(self) -> SecureAuthenticationSession:
        """Provide SecureAuthenticationSession instance for testing."""
        config = AuthConfig(session_duration_hours=2, auth_method="midway")
        return SecureAuthenticationSession(config)
    
    def test_initialization_sets_security_level(self, secure_session: SecureAuthenticationSession) -> None:
        """Test initialization sets enhanced security level."""
        assert secure_session._security_level == "enhanced"
    
    @patch.dict('os.environ', {}, clear=True)
    def test_start_session_validates_security_context(self, secure_session: SecureAuthenticationSession) -> None:
        """Test start_session validates security context."""
        # Should succeed with clean environment
        secure_session.start_session()
        
        assert secure_session._metadata is not None
        assert secure_session._metadata.security_level == "enhanced"
    
    @patch.dict('os.environ', {'TICKET_ANALYZER_INSECURE_MODE': '1'})
    def test_start_session_rejects_insecure_mode(self, secure_session: SecureAuthenticationSession) -> None:
        """Test start_session rejects insecure mode."""
        with pytest.raises(SecurityError) as exc_info:
            secure_session.start_session()
        
        assert "Cannot start secure session in insecure mode" in str(exc_info.value)
    
    @patch('gc.collect')
    def test_end_session_performs_secure_cleanup(
        self, mock_gc: Mock, secure_session: SecureAuthenticationSession
    ) -> None:
        """Test end_session performs enhanced secure cleanup."""
        secure_session.start_session()
        secure_session.end_session()
        
        # Should call garbage collection multiple times
        assert mock_gc.call_count >= 3
    
    def test_get_session_metadata_includes_security_info(self, secure_session: SecureAuthenticationSession) -> None:
        """Test get_session_metadata includes security information."""
        secure_session.start_session()
        
        metadata = secure_session.get_session_metadata()
        
        assert metadata["security_level"] == "enhanced"
        assert metadata["memory_protection"] == "enabled"
        assert metadata["secure_cleanup"] == "enabled"
        assert metadata["credential_protection"] == "enhanced"
    
    def test_get_session_metadata_sanitizes_sensitive_data(self, secure_session: SecureAuthenticationSession) -> None:
        """Test get_session_metadata sanitizes sensitive data."""
        secure_session.start_session()
        
        # Add sensitive data to metadata
        secure_session._metadata.user_info = {
            "username": "testuser",
            "credentials": "secret123",
            "tokens": "abc123"
        }
        
        metadata = secure_session.get_session_metadata()
        
        # Sensitive fields should be redacted
        assert metadata["user_info"] == "[REDACTED]"
    
    def test_secure_memory_cleanup_removes_cached_credentials(self, secure_session: SecureAuthenticationSession) -> None:
        """Test secure memory cleanup removes cached credentials."""
        # Add cached credentials attribute
        secure_session._cached_credentials = "secret_data"
        
        secure_session._secure_memory_cleanup()
        
        # Cached credentials should be removed
        assert not hasattr(secure_session, '_cached_credentials')


class TestSessionThreadSafety:
    """Test cases for session thread safety."""
    
    @pytest.fixture
    def thread_safe_session(self) -> AuthenticationSession:
        """Provide session for thread safety testing."""
        config = AuthConfig(session_duration_hours=1)
        return AuthenticationSession(config)
    
    def test_concurrent_start_session_calls(self, thread_safe_session: AuthenticationSession) -> None:
        """Test concurrent start_session calls are handled safely."""
        results = []
        errors = []
        
        def start_session_thread():
            try:
                thread_safe_session.start_session()
                results.append(True)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=start_session_thread)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have no errors and at least one success
        assert len(errors) == 0
        assert len(results) > 0
        assert thread_safe_session._metadata is not None
    
    def test_concurrent_session_operations(self, thread_safe_session: AuthenticationSession) -> None:
        """Test concurrent session operations are handled safely."""
        thread_safe_session.start_session()
        
        results = {"valid": [], "refresh": [], "metadata": []}
        errors = []
        
        def session_operations():
            try:
                # Perform various session operations
                valid = thread_safe_session.is_session_valid()
                refresh = thread_safe_session.refresh_session()
                metadata = thread_safe_session.get_session_metadata()
                
                results["valid"].append(valid)
                results["refresh"].append(refresh)
                results["metadata"].append(metadata)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads performing operations
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=session_operations)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have no errors
        assert len(errors) == 0
        assert len(results["valid"]) == 10
        assert len(results["refresh"]) == 10
        assert len(results["metadata"]) == 10
    
    def test_concurrent_cleanup_callbacks(self, thread_safe_session: AuthenticationSession) -> None:
        """Test concurrent cleanup callback operations are handled safely."""
        callback_calls = []
        
        def test_callback():
            callback_calls.append(threading.current_thread().ident)
        
        # Add callbacks from multiple threads
        def add_callback_thread():
            thread_safe_session.add_cleanup_callback(test_callback)
        
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=add_callback_thread)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Start session and end it to trigger callbacks
        thread_safe_session.start_session()
        thread_safe_session.end_session()
        
        # All callbacks should have been called
        assert len(callback_calls) == 5


class TestSessionIntegration:
    """Integration tests for session management."""
    
    @pytest.fixture
    def integration_config(self) -> AuthConfig:
        """Provide configuration for integration tests."""
        return AuthConfig(
            session_duration_hours=1,
            check_interval_seconds=1,
            auth_method="midway",
            auto_refresh=True
        )
    
    def test_complete_session_lifecycle(self, integration_config: AuthConfig) -> None:
        """Test complete session lifecycle from start to end."""
        session = AuthenticationSession(integration_config)
        
        # Initially no session
        assert session.is_session_valid() is False
        assert session.get_session_metadata()["active"] is False
        
        # Start session
        session.start_session()
        assert session.is_session_valid() is True
        
        metadata = session.get_session_metadata()
        assert metadata["active"] is True
        assert metadata["session_id"] is not None
        
        # Refresh session
        original_expiry = session._metadata.expiry_time
        refresh_result = session.refresh_session()
        assert refresh_result is True
        assert session._metadata.expiry_time > original_expiry
        
        # End session
        session.end_session()
        assert session.is_session_valid() is False
        assert session.get_session_metadata()["active"] is False
    
    def test_session_expiry_handling(self, integration_config: AuthConfig) -> None:
        """Test session expiry detection and cleanup."""
        session = AuthenticationSession(integration_config)
        
        # Start session
        session.start_session()
        assert session.is_session_valid() is True
        
        # Manually expire session
        session._metadata.expiry_time = datetime.now() - timedelta(minutes=1)
        
        # Should detect expiry and clean up
        assert session.is_session_valid() is False
        assert session._metadata is None
    
    def test_session_with_cleanup_callbacks(self, integration_config: AuthConfig) -> None:
        """Test session with cleanup callbacks integration."""
        session = AuthenticationSession(integration_config)
        
        callback_results = []
        
        def cleanup_callback():
            callback_results.append("cleanup_executed")
        
        def error_callback():
            raise Exception("Callback error")
        
        # Add callbacks
        session.add_cleanup_callback(cleanup_callback)
        session.add_cleanup_callback(error_callback)
        
        # Start and end session
        session.start_session()
        session.end_session()
        
        # Cleanup callback should have been executed despite error callback
        assert "cleanup_executed" in callback_results
    
    def test_session_context_manager_integration(self, integration_config: AuthConfig) -> None:
        """Test session context manager integration."""
        callback_executed = []
        
        def cleanup_callback():
            callback_executed.append(True)
        
        with AuthenticationSession(integration_config) as session:
            session.add_cleanup_callback(cleanup_callback)
            session.start_session()
            
            assert session.is_session_valid() is True
        
        # Session should be cleaned up and callbacks executed
        assert len(callback_executed) == 1
    
    def test_secure_session_integration(self) -> None:
        """Test secure session integration with enhanced features."""
        config = AuthConfig(session_duration_hours=1, auth_method="midway")
        
        with SecureAuthenticationSession(config) as session:
            session.start_session()
            
            metadata = session.get_session_metadata()
            assert metadata["security_level"] == "enhanced"
            assert metadata["memory_protection"] == "enabled"
            assert metadata["secure_cleanup"] == "enabled"
            
            # Test secure refresh
            refresh_result = session.refresh_session()
            assert refresh_result is True
        
        # Session should be securely cleaned up