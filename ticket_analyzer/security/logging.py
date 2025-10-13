"""Secure logging and error handling for ticket analyzer.

This module provides secure logging capabilities with:
- Credential filtering and sanitization
- Secure error message handling
- Log sanitization for authentication operations
- Structured logging with security considerations
"""

from __future__ import annotations
import logging
import logging.handlers
import re
import traceback
import sys
import os
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

from .sanitizer import TicketDataSanitizer, SanitizationRule, SensitivityLevel


@dataclass
class LoggingConfig:
    """Configuration for secure logging."""
    log_level: str = "INFO"
    log_file: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    sanitize_logs: bool = True
    include_sensitive_debug: bool = False
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class SecureFormatter(logging.Formatter):
    """Secure log formatter that sanitizes sensitive information."""
    
    def __init__(self, 
                 fmt: Optional[str] = None,
                 sanitizer: Optional[TicketDataSanitizer] = None) -> None:
        super().__init__(fmt)
        self._sanitizer = sanitizer or TicketDataSanitizer()
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with sanitization."""
        # Sanitize the message
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self._sanitizer.sanitize_log_message(record.msg)
        
        # Sanitize arguments if present
        if hasattr(record, 'args') and record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    sanitized_args.append(self._sanitizer.sanitize_log_message(arg))
                elif isinstance(arg, dict):
                    sanitized_args.append(self._sanitizer.sanitize_ticket_data(arg))
                else:
                    sanitized_args.append(arg)
            record.args = tuple(sanitized_args)
        
        # Sanitize exception information
        if record.exc_info:
            record.exc_text = self._sanitize_exception_info(record.exc_info)
        
        return super().format(record)
    
    def _sanitize_exception_info(self, exc_info: tuple) -> str:
        """Sanitize exception information."""
        try:
            exc_text = ''.join(traceback.format_exception(*exc_info))
            return self._sanitizer.sanitize_error_message(exc_text)
        except Exception:
            return "[EXCEPTION_INFO_REDACTED]"


class SecureLogger:
    """Secure logger with credential filtering and sanitization."""
    
    # Patterns for sensitive data detection in logs
    SENSITIVE_LOG_PATTERNS = [
        # Authentication tokens and credentials
        r'(?i)(token|auth|credential|password|secret|key)\s*[:=]\s*[^\s]+',
        # API keys and access tokens
        r'(?i)(api[_-]?key|access[_-]?token|bearer)\s*[:=]\s*[^\s]+',
        # Session identifiers
        r'(?i)(session[_-]?id|cookie)\s*[:=]\s*[^\s]+',
        # Database connection strings
        r'(?i)(connection[_-]?string|db[_-]?url)\s*[:=]\s*[^\s]+',
        # File paths that might contain sensitive info
        r'/home/[^/\s]+/\.[^/\s]*',
        # Command line arguments that might be sensitive
        r'--(?:password|token|key|secret)\s+[^\s]+',
    ]
    
    def __init__(self, 
                 name: str,
                 config: Optional[LoggingConfig] = None) -> None:
        """Initialize secure logger."""
        self._config = config or LoggingConfig()
        self._sanitizer = TicketDataSanitizer(
            sensitivity_threshold=SensitivityLevel.LOW
        )
        self._logger = self._setup_logger(name)
    
    def _setup_logger(self, name: str) -> logging.Logger:
        """Set up logger with secure configuration."""
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, self._config.log_level.upper()))
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Create secure formatter
        formatter = SecureFormatter(
            fmt=self._config.log_format,
            sanitizer=self._sanitizer
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler if specified
        if self._config.log_file:
            self._setup_file_handler(logger, formatter)
        
        return logger
    
    def _setup_file_handler(self, 
                           logger: logging.Logger, 
                           formatter: SecureFormatter) -> None:
        """Set up secure file handler."""
        log_file_path = Path(self._config.log_file)
        
        # Ensure log directory exists with secure permissions
        log_file_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        
        # Use rotating file handler for log management
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file_path,
            maxBytes=self._config.max_file_size,
            backupCount=self._config.backup_count
        )
        
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Set secure permissions on log file
        try:
            os.chmod(log_file_path, 0o600)
        except OSError as e:
            logger.warning(f"Could not set secure permissions on log file: {e}")
    
    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message with sanitization."""
        if self._config.include_sensitive_debug:
            # In debug mode, log with extra sanitization
            sanitized_message = self._extra_sanitize_debug(message)
            self._logger.debug(sanitized_message, *args, **kwargs)
        else:
            self._logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log info message."""
        self._logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message."""
        self._logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log error message."""
        self._logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log critical message."""
        self._logger.critical(message, *args, **kwargs)
    
    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Log exception with sanitized traceback."""
        self._logger.exception(message, *args, **kwargs)
    
    def log_authentication_attempt(self, 
                                  success: bool, 
                                  details: Optional[Dict[str, Any]] = None) -> None:
        """Log authentication attempt with sanitization."""
        sanitized_details = {}
        if details:
            sanitized_details = self._sanitizer.sanitize_ticket_data(details)
        
        if success:
            self.info(f"Authentication successful: {sanitized_details}")
        else:
            self.warning(f"Authentication failed: {sanitized_details}")
    
    def log_data_access(self, 
                       operation: str, 
                       resource: str, 
                       success: bool,
                       details: Optional[Dict[str, Any]] = None) -> None:
        """Log data access operations with sanitization."""
        sanitized_details = {}
        if details:
            sanitized_details = self._sanitizer.sanitize_ticket_data(details)
        
        status = "SUCCESS" if success else "FAILED"
        self.info(f"Data access {operation} on {resource}: {status} - {sanitized_details}")
    
    def log_security_event(self, 
                          event_type: str, 
                          severity: str,
                          details: Dict[str, Any]) -> None:
        """Log security events with proper sanitization."""
        sanitized_details = self._sanitizer.sanitize_ticket_data(details)
        
        log_method = getattr(self, severity.lower(), self.info)
        log_method(f"SECURITY EVENT [{event_type}]: {sanitized_details}")
    
    def _extra_sanitize_debug(self, message: str) -> str:
        """Apply extra sanitization for debug messages."""
        sanitized = message
        
        for pattern in self.SENSITIVE_LOG_PATTERNS:
            sanitized = re.sub(pattern, '[SENSITIVE_DATA_REDACTED]', sanitized)
        
        return sanitized


class SecureErrorHandler:
    """Handle errors with sanitized messages and secure logging."""
    
    def __init__(self, 
                 logger: Optional[SecureLogger] = None,
                 sanitizer: Optional[TicketDataSanitizer] = None) -> None:
        """Initialize secure error handler."""
        self._logger = logger or SecureLogger(__name__)
        self._sanitizer = sanitizer or TicketDataSanitizer()
    
    def sanitize_exception_message(self, exception: Exception) -> str:
        """Sanitize exception message to prevent information leakage."""
        message = str(exception)
        return self._sanitizer.sanitize_error_message(message)
    
    def sanitize_traceback(self, tb: Optional[str] = None) -> str:
        """Sanitize traceback information."""
        if tb is None:
            tb = traceback.format_exc()
        
        # Remove file paths that might contain sensitive information
        sanitized_tb = re.sub(
            r'/[^\s]*/(ticket_analyzer|\.ticket-analyzer)/[^\s]*',
            '[PATH_REDACTED]',
            tb
        )
        
        # Remove line numbers and file details that might leak info
        sanitized_tb = re.sub(
            r'File "[^"]*", line \d+',
            'File "[REDACTED]", line [REDACTED]',
            sanitized_tb
        )
        
        # Sanitize any other sensitive data in traceback
        return self._sanitizer.sanitize_error_message(sanitized_tb)
    
    def log_sanitized_error(self, 
                           exception: Exception, 
                           context: Optional[Dict[str, Any]] = None,
                           include_traceback: bool = True) -> None:
        """Log error with sanitized information."""
        sanitized_message = self.sanitize_exception_message(exception)
        
        error_info = {
            'error_type': type(exception).__name__,
            'message': sanitized_message,
            'timestamp': datetime.now().isoformat()
        }
        
        if include_traceback:
            error_info['traceback'] = self.sanitize_traceback()
        
        if context:
            sanitized_context = self._sanitizer.sanitize_ticket_data(context)
            error_info['context'] = sanitized_context
        
        self._logger.error(f"Sanitized error: {error_info}")
    
    def handle_authentication_error(self, 
                                   exception: Exception,
                                   operation: str = "authentication") -> str:
        """Handle authentication errors with secure logging."""
        sanitized_message = self.sanitize_exception_message(exception)
        
        # Log security event
        self._logger.log_security_event(
            event_type="AUTHENTICATION_ERROR",
            severity="warning",
            details={
                'operation': operation,
                'error_type': type(exception).__name__,
                'timestamp': datetime.now().isoformat()
            }
        )
        
        # Return user-friendly message
        return f"Authentication failed during {operation}. Please check your credentials."
    
    def handle_data_access_error(self, 
                                exception: Exception,
                                resource: str = "ticket_data") -> str:
        """Handle data access errors with secure logging."""
        sanitized_message = self.sanitize_exception_message(exception)
        
        self._logger.log_security_event(
            event_type="DATA_ACCESS_ERROR",
            severity="error",
            details={
                'resource': resource,
                'error_type': type(exception).__name__,
                'timestamp': datetime.now().isoformat()
            }
        )
        
        return f"Failed to access {resource}. Please try again later."
    
    def create_safe_error_response(self, 
                                  exception: Exception,
                                  default_message: str = "An error occurred") -> Dict[str, Any]:
        """Create safe error response for API/CLI output."""
        return {
            'error': True,
            'message': default_message,
            'error_type': type(exception).__name__,
            'timestamp': datetime.now().isoformat(),
            # Don't include sensitive details in response
        }


class AuditLogger(SecureLogger):
    """Specialized logger for audit events."""
    
    def __init__(self, config: Optional[LoggingConfig] = None) -> None:
        """Initialize audit logger."""
        audit_config = config or LoggingConfig()
        if not audit_config.log_file:
            # Default audit log location
            audit_config.log_file = str(Path.home() / ".ticket-analyzer" / "audit.log")
        
        super().__init__("audit", audit_config)
    
    def log_user_action(self, 
                       action: str, 
                       user: str,
                       resource: Optional[str] = None,
                       details: Optional[Dict[str, Any]] = None) -> None:
        """Log user actions for audit purposes."""
        audit_entry = {
            'action': action,
            'user': user,
            'timestamp': datetime.now().isoformat(),
            'resource': resource or 'unknown'
        }
        
        if details:
            audit_entry['details'] = self._sanitizer.sanitize_ticket_data(details)
        
        self.info(f"AUDIT: {audit_entry}")
    
    def log_data_modification(self, 
                             operation: str,
                             data_type: str,
                             user: str,
                             before: Optional[Dict[str, Any]] = None,
                             after: Optional[Dict[str, Any]] = None) -> None:
        """Log data modification events."""
        audit_entry = {
            'operation': operation,
            'data_type': data_type,
            'user': user,
            'timestamp': datetime.now().isoformat()
        }
        
        if before:
            audit_entry['before'] = self._sanitizer.sanitize_ticket_data(before)
        if after:
            audit_entry['after'] = self._sanitizer.sanitize_ticket_data(after)
        
        self.info(f"DATA_MODIFICATION: {audit_entry}")
    
    def log_security_violation(self, 
                              violation_type: str,
                              user: str,
                              details: Dict[str, Any]) -> None:
        """Log security violations."""
        violation_entry = {
            'violation_type': violation_type,
            'user': user,
            'timestamp': datetime.now().isoformat(),
            'details': self._sanitizer.sanitize_ticket_data(details)
        }
        
        self.critical(f"SECURITY_VIOLATION: {violation_entry}")


def setup_secure_logging(config: Optional[LoggingConfig] = None) -> SecureLogger:
    """Set up secure logging for the application."""
    return SecureLogger("ticket_analyzer", config)


def get_logger(name: str) -> SecureLogger:
    """Get a secure logger instance."""
    return SecureLogger(name)