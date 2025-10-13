"""Structured logging system for ticket analyzer.

This module provides secure, structured logging with JSON format support,
log rotation, and sanitization of sensitive data.
"""

from __future__ import annotations
import json
import logging
import logging.handlers
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict

from ..security.sanitizer import TicketDataSanitizer


@dataclass
class LogConfig:
    """Configuration for logging system."""
    level: str = "INFO"
    format_type: str = "structured"  # "structured" or "simple"
    log_file: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    sanitize_logs: bool = True
    console_output: bool = True
    json_format: bool = False


class SecureLogFormatter(logging.Formatter):
    """Secure log formatter with data sanitization."""
    
    def __init__(self, sanitizer: Optional[TicketDataSanitizer] = None,
                 json_format: bool = False) -> None:
        super().__init__()
        self._sanitizer = sanitizer or TicketDataSanitizer()
        self._json_format = json_format
        
        # Sensitive patterns to redact in log messages
        self._sensitive_patterns = [
            (r'password["\s]*[:=]["\s]*[^\s"]+', '[PASSWORD_REDACTED]'),
            (r'token["\s]*[:=]["\s]*[^\s"]+', '[TOKEN_REDACTED]'),
            (r'secret["\s]*[:=]["\s]*[^\s"]+', '[SECRET_REDACTED]'),
            (r'key["\s]*[:=]["\s]*[^\s"]+', '[KEY_REDACTED]'),
            (r'auth["\s]*[:=]["\s]*[^\s"]+', '[AUTH_REDACTED]'),
            (r'credential["\s]*[:=]["\s]*[^\s"]+', '[CREDENTIAL_REDACTED]'),
        ]
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with sanitization."""
        # Sanitize the message
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self._sanitize_message(record.msg)
        
        # Sanitize arguments
        if hasattr(record, 'args') and record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    sanitized_args.append(self._sanitize_message(arg))
                elif isinstance(arg, dict):
                    sanitized_args.append(self._sanitizer.sanitize_ticket_data(arg))
                else:
                    sanitized_args.append(arg)
            record.args = tuple(sanitized_args)
        
        if self._json_format:
            return self._format_json(record)
        else:
            return self._format_structured(record)
    
    def _sanitize_message(self, message: str) -> str:
        """Sanitize log message to remove sensitive information."""
        sanitized = message
        for pattern, replacement in self._sensitive_patterns:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        return sanitized
    
    def _format_json(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in {'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info'}:
                log_data[key] = value
        
        return json.dumps(log_data, default=str)
    
    def _format_structured(self, record: logging.LogRecord) -> str:
        """Format log record in structured text format."""
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        base_format = (
            f"{timestamp} | {record.levelname:8} | "
            f"{record.name:20} | {record.module}:{record.funcName}:{record.lineno} | "
            f"{record.getMessage()}"
        )
        
        if record.exc_info:
            base_format += f"\n{self.formatException(record.exc_info)}"
        
        return base_format


class LoggerManager:
    """Centralized logger management with security and performance features."""
    
    def __init__(self, config: Optional[LogConfig] = None) -> None:
        self._config = config or LogConfig()
        self._sanitizer = TicketDataSanitizer()
        self._loggers: Dict[str, logging.Logger] = {}
        self._setup_root_logger()
    
    def _setup_root_logger(self) -> None:
        """Set up the root logger configuration."""
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self._config.level.upper()))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Create formatter
        formatter = SecureLogFormatter(
            sanitizer=self._sanitizer,
            json_format=self._config.json_format
        )
        
        # Console handler
        if self._config.console_output:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # File handler with rotation
        if self._config.log_file:
            self._setup_file_handler(root_logger, formatter)
    
    def _setup_file_handler(self, logger: logging.Logger, 
                           formatter: SecureLogFormatter) -> None:
        """Set up rotating file handler with secure permissions."""
        log_path = Path(self._config.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_path),
            maxBytes=self._config.max_file_size,
            backupCount=self._config.backup_count,
            encoding='utf-8'
        )
        
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Set secure permissions on log file
        if log_path.exists():
            log_path.chmod(0o600)
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger with the specified name."""
        if name not in self._loggers:
            logger = logging.getLogger(name)
            self._loggers[name] = logger
        
        return self._loggers[name]
    
    def update_config(self, config: LogConfig) -> None:
        """Update logging configuration."""
        self._config = config
        self._setup_root_logger()
        
        # Update existing loggers
        for logger in self._loggers.values():
            logger.setLevel(getattr(logging, self._config.level.upper()))
    
    def set_level(self, level: str) -> None:
        """Set logging level for all loggers."""
        log_level = getattr(logging, level.upper())
        
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        for logger in self._loggers.values():
            logger.setLevel(log_level)
    
    def add_context_filter(self, context: Dict[str, Any]) -> None:
        """Add context information to all log records."""
        class ContextFilter(logging.Filter):
            def filter(self, record: logging.LogRecord) -> bool:
                for key, value in context.items():
                    setattr(record, key, value)
                return True
        
        context_filter = ContextFilter()
        root_logger = logging.getLogger()
        root_logger.addFilter(context_filter)
    
    def log_performance_metric(self, operation: str, duration: float,
                              metadata: Optional[Dict[str, Any]] = None) -> None:
        """Log performance metrics in structured format."""
        perf_logger = self.get_logger("performance")
        
        metric_data = {
            "operation": operation,
            "duration_ms": round(duration * 1000, 2),
            "timestamp": datetime.now().isoformat()
        }
        
        if metadata:
            # Sanitize metadata before logging
            sanitized_metadata = self._sanitizer.sanitize_ticket_data(metadata)
            metric_data.update(sanitized_metadata)
        
        perf_logger.info("Performance metric", extra=metric_data)
    
    def log_security_event(self, event_type: str, details: Dict[str, Any],
                          severity: str = "WARNING") -> None:
        """Log security-related events with proper sanitization."""
        security_logger = self.get_logger("security")
        
        # Sanitize security event details
        sanitized_details = self._sanitizer.sanitize_ticket_data(details)
        
        event_data = {
            "event_type": event_type,
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
            "details": sanitized_details
        }
        
        log_level = getattr(logging, severity.upper(), logging.WARNING)
        security_logger.log(log_level, f"Security event: {event_type}", extra=event_data)
    
    def flush_logs(self) -> None:
        """Flush all log handlers."""
        for handler in logging.getLogger().handlers:
            handler.flush()
    
    def close_handlers(self) -> None:
        """Close all log handlers."""
        for handler in logging.getLogger().handlers:
            handler.close()


class SecureLogger:
    """Wrapper for secure logging operations."""
    
    def __init__(self, name: str, manager: Optional[LoggerManager] = None) -> None:
        self._manager = manager or LoggerManager()
        self._logger = self._manager.get_logger(name)
        self._sanitizer = TicketDataSanitizer()
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message with sanitization."""
        sanitized_kwargs = self._sanitize_kwargs(kwargs)
        self._logger.debug(message, extra=sanitized_kwargs)
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message with sanitization."""
        sanitized_kwargs = self._sanitize_kwargs(kwargs)
        self._logger.info(message, extra=sanitized_kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message with sanitization."""
        sanitized_kwargs = self._sanitize_kwargs(kwargs)
        self._logger.warning(message, extra=sanitized_kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message with sanitization."""
        sanitized_kwargs = self._sanitize_kwargs(kwargs)
        self._logger.error(message, extra=sanitized_kwargs)
    
    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message with sanitization."""
        sanitized_kwargs = self._sanitize_kwargs(kwargs)
        self._logger.critical(message, extra=sanitized_kwargs)
    
    def exception(self, message: str, **kwargs: Any) -> None:
        """Log exception with sanitized traceback."""
        sanitized_kwargs = self._sanitize_kwargs(kwargs)
        self._logger.exception(message, extra=sanitized_kwargs)
    
    def _sanitize_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize keyword arguments for logging."""
        return self._sanitizer.sanitize_ticket_data(kwargs)


# Global logger manager instance
_global_manager: Optional[LoggerManager] = None


def get_logger(name: str) -> SecureLogger:
    """Get a secure logger instance."""
    global _global_manager
    if _global_manager is None:
        _global_manager = LoggerManager()
    
    return SecureLogger(name, _global_manager)


def configure_logging(config: LogConfig) -> None:
    """Configure global logging settings."""
    global _global_manager
    if _global_manager is None:
        _global_manager = LoggerManager(config)
    else:
        _global_manager.update_config(config)


def set_log_level(level: str) -> None:
    """Set global log level."""
    global _global_manager
    if _global_manager is None:
        _global_manager = LoggerManager()
    
    _global_manager.set_level(level)


def add_log_context(context: Dict[str, Any]) -> None:
    """Add context to all log messages."""
    global _global_manager
    if _global_manager is None:
        _global_manager = LoggerManager()
    
    _global_manager.add_context_filter(context)