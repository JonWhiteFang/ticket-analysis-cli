"""Custom exception hierarchy for ticket analysis operations.

This module defines a comprehensive exception hierarchy that provides specific
error types for different failure scenarios throughout the application.
All exceptions include proper error messages and context information.
"""

from __future__ import annotations
from typing import Optional, Dict, Any


class TicketAnalysisError(Exception):
    """Base exception for all ticket analysis errors.
    
    This is the root exception class that all other custom exceptions
    inherit from. It provides a consistent interface for error handling
    throughout the application with support for additional context information.
    
    Attributes:
        message: Human-readable error message
        details: Additional context information about the error
        error_code: Optional error code for programmatic handling
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, 
                 error_code: Optional[str] = None) -> None:
        """Initialize the exception with message and optional details.
        
        Args:
            message: Human-readable error message.
            details: Additional context information about the error.
            error_code: Optional error code for programmatic handling.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.error_code = error_code
    
    def __str__(self) -> str:
        """Return string representation of the exception.
        
        Returns:
            Formatted error message with details if available.
        """
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message
    
    def __repr__(self) -> str:
        """Return detailed string representation for debugging.
        
        Returns:
            Detailed representation including class name and all attributes.
        """
        return (f"{self.__class__.__name__}(message='{self.message}', "
                f"details={self.details}, error_code='{self.error_code}')")
    
    def add_detail(self, key: str, value: Any) -> None:
        """Add additional detail information to the exception.
        
        Args:
            key: Detail key.
            value: Detail value.
        """
        self.details[key] = value
    
    def get_detail(self, key: str, default: Any = None) -> Any:
        """Get a specific detail value.
        
        Args:
            key: Detail key to retrieve.
            default: Default value if key not found.
            
        Returns:
            Detail value or default if not found.
        """
        return self.details.get(key, default)


class AuthenticationError(TicketAnalysisError):
    """Raised when authentication operations fail.
    
    This includes failures in Midway authentication, session timeouts,
    credential validation errors, and permission issues.
    
    Common scenarios:
    - Midway authentication failure
    - Session timeout or expiration
    - Invalid credentials
    - Insufficient permissions
    - Authentication service unavailable
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None,
                 auth_method: Optional[str] = None) -> None:
        """Initialize authentication error.
        
        Args:
            message: Error message.
            details: Additional error details.
            auth_method: Authentication method that failed.
        """
        super().__init__(message, details, "AUTH_ERROR")
        if auth_method:
            self.add_detail("auth_method", auth_method)


class ConfigurationError(TicketAnalysisError):
    """Raised when configuration is invalid or missing.
    
    This includes malformed configuration files, missing required settings,
    invalid configuration values, and configuration validation failures.
    
    Common scenarios:
    - Missing configuration file
    - Invalid JSON/YAML syntax
    - Missing required configuration keys
    - Invalid configuration values
    - Configuration validation failures
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None,
                 config_file: Optional[str] = None, config_key: Optional[str] = None) -> None:
        """Initialize configuration error.
        
        Args:
            message: Error message.
            details: Additional error details.
            config_file: Configuration file that caused the error.
            config_key: Specific configuration key that is invalid.
        """
        super().__init__(message, details, "CONFIG_ERROR")
        if config_file:
            self.add_detail("config_file", config_file)
        if config_key:
            self.add_detail("config_key", config_key)


class DataRetrievalError(TicketAnalysisError):
    """Raised when data retrieval operations fail.
    
    This includes MCP connection failures, API errors, network timeouts,
    data parsing errors, and external service unavailability.
    
    Common scenarios:
    - MCP server connection failure
    - API request timeout
    - Network connectivity issues
    - Invalid API response format
    - External service unavailable
    - Rate limiting exceeded
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None,
                 service: Optional[str] = None, operation: Optional[str] = None) -> None:
        """Initialize data retrieval error.
        
        Args:
            message: Error message.
            details: Additional error details.
            service: Service that failed (e.g., 'MCP', 'API').
            operation: Specific operation that failed.
        """
        super().__init__(message, details, "DATA_ERROR")
        if service:
            self.add_detail("service", service)
        if operation:
            self.add_detail("operation", operation)


class AnalysisError(TicketAnalysisError):
    """Raised when analysis operations fail.
    
    This includes calculation errors, invalid data for analysis,
    processing failures, and statistical computation errors.
    
    Common scenarios:
    - Invalid input data for analysis
    - Mathematical calculation errors
    - Insufficient data for analysis
    - Memory errors during processing
    - Algorithm convergence failures
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None,
                 analysis_type: Optional[str] = None, data_size: Optional[int] = None) -> None:
        """Initialize analysis error.
        
        Args:
            message: Error message.
            details: Additional error details.
            analysis_type: Type of analysis that failed.
            data_size: Size of data being analyzed.
        """
        super().__init__(message, details, "ANALYSIS_ERROR")
        if analysis_type:
            self.add_detail("analysis_type", analysis_type)
        if data_size:
            self.add_detail("data_size", data_size)


class ValidationError(TicketAnalysisError):
    """Raised when data validation fails.
    
    This includes input validation errors, data format issues,
    security validation failures, and constraint violations.
    
    Common scenarios:
    - Invalid input format
    - Security policy violations
    - Data constraint violations
    - Schema validation failures
    - Business rule violations
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None,
                 field_name: Optional[str] = None, validation_rule: Optional[str] = None) -> None:
        """Initialize validation error.
        
        Args:
            message: Error message.
            details: Additional error details.
            field_name: Name of the field that failed validation.
            validation_rule: Validation rule that was violated.
        """
        super().__init__(message, details, "VALIDATION_ERROR")
        if field_name:
            self.add_detail("field_name", field_name)
        if validation_rule:
            self.add_detail("validation_rule", validation_rule)


# MCP-specific exceptions
class MCPError(DataRetrievalError):
    """Base class for MCP-related errors.
    
    Raised when MCP (Model Context Protocol) operations fail.
    This is a specialized data retrieval error for MCP-specific issues.
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None,
                 mcp_method: Optional[str] = None) -> None:
        """Initialize MCP error.
        
        Args:
            message: Error message.
            details: Additional error details.
            mcp_method: MCP method that failed.
        """
        super().__init__(message, details, "MCP", mcp_method)
        self.error_code = "MCP_ERROR"


class MCPConnectionError(MCPError):
    """Raised when MCP connection fails.
    
    This includes server startup failures, connection timeouts,
    and communication protocol errors.
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None,
                 server_command: Optional[str] = None) -> None:
        """Initialize MCP connection error.
        
        Args:
            message: Error message.
            details: Additional error details.
            server_command: MCP server command that failed.
        """
        super().__init__(message, details, "connect")
        self.error_code = "MCP_CONNECTION_ERROR"
        if server_command:
            self.add_detail("server_command", server_command)


class MCPTimeoutError(MCPError):
    """Raised when MCP operations timeout.
    
    This includes request timeouts, response timeouts,
    and connection establishment timeouts.
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None,
                 timeout_duration: Optional[float] = None) -> None:
        """Initialize MCP timeout error.
        
        Args:
            message: Error message.
            details: Additional error details.
            timeout_duration: Timeout duration in seconds.
        """
        super().__init__(message, details, "timeout")
        self.error_code = "MCP_TIMEOUT_ERROR"
        if timeout_duration:
            self.add_detail("timeout_duration", timeout_duration)


class MCPAuthenticationError(MCPError):
    """Raised when MCP authentication fails.
    
    This includes authentication token issues, permission errors,
    and credential validation failures specific to MCP.
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Initialize MCP authentication error.
        
        Args:
            message: Error message.
            details: Additional error details.
        """
        super().__init__(message, details, "authenticate")
        self.error_code = "MCP_AUTH_ERROR"


# Circuit breaker and resilience exceptions
class CircuitBreakerOpenError(DataRetrievalError):
    """Raised when circuit breaker is open.
    
    This indicates that too many failures have occurred and the
    circuit breaker has opened to prevent further requests.
    """
    
    def __init__(self, message: str = "Circuit breaker is open", 
                 details: Optional[Dict[str, Any]] = None,
                 failure_count: Optional[int] = None) -> None:
        """Initialize circuit breaker error.
        
        Args:
            message: Error message.
            details: Additional error details.
            failure_count: Number of failures that triggered the circuit breaker.
        """
        super().__init__(message, details, "circuit_breaker", "open")
        self.error_code = "CIRCUIT_BREAKER_OPEN"
        if failure_count:
            self.add_detail("failure_count", failure_count)


# Data processing exceptions
class DataProcessingError(AnalysisError):
    """Raised when data processing fails.
    
    This includes data transformation errors, parsing failures,
    and data format conversion issues.
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None,
                 processing_stage: Optional[str] = None) -> None:
        """Initialize data processing error.
        
        Args:
            message: Error message.
            details: Additional error details.
            processing_stage: Stage of processing that failed.
        """
        super().__init__(message, details, "data_processing")
        self.error_code = "DATA_PROCESSING_ERROR"
        if processing_stage:
            self.add_detail("processing_stage", processing_stage)


# Report generation exceptions
class ReportGenerationError(TicketAnalysisError):
    """Raised when report generation fails.
    
    This includes template rendering errors, file I/O issues,
    and report formatting failures.
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None,
                 report_format: Optional[str] = None, template_name: Optional[str] = None) -> None:
        """Initialize report generation error.
        
        Args:
            message: Error message.
            details: Additional error details.
            report_format: Format of report being generated.
            template_name: Template that failed to render.
        """
        super().__init__(message, details, "REPORT_ERROR")
        if report_format:
            self.add_detail("report_format", report_format)
        if template_name:
            self.add_detail("template_name", template_name)


# Security exceptions
class SecurityError(TicketAnalysisError):
    """Raised when security violations are detected.
    
    This includes unauthorized access attempts, data sanitization
    failures, and security policy violations.
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None,
                 security_rule: Optional[str] = None) -> None:
        """Initialize security error.
        
        Args:
            message: Error message.
            details: Additional error details.
            security_rule: Security rule that was violated.
        """
        super().__init__(message, details, "SECURITY_ERROR")
        if security_rule:
            self.add_detail("security_rule", security_rule)


# CLI-specific exceptions
class CLIError(TicketAnalysisError):
    """Raised when CLI operations fail.
    
    This includes command parsing errors, argument validation failures,
    and CLI-specific operational issues.
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None,
                 command: Optional[str] = None, exit_code: int = 1) -> None:
        """Initialize CLI error.
        
        Args:
            message: Error message.
            details: Additional error details.
            command: CLI command that failed.
            exit_code: Exit code for the CLI.
        """
        super().__init__(message, details, "CLI_ERROR")
        if command:
            self.add_detail("command", command)
        self.add_detail("exit_code", exit_code)


# File operation exceptions
class FileOperationError(TicketAnalysisError):
    """Raised when file operations fail.
    
    This includes file I/O errors, permission issues,
    and file system related failures.
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None,
                 file_path: Optional[str] = None, operation: Optional[str] = None) -> None:
        """Initialize file operation error.
        
        Args:
            message: Error message.
            details: Additional error details.
            file_path: Path to file that caused the error.
            operation: File operation that failed (read, write, delete, etc.).
        """
        super().__init__(message, details, "FILE_ERROR")
        if file_path:
            self.add_detail("file_path", file_path)
        if operation:
            self.add_detail("operation", operation)


# Utility functions for exception handling
def create_error_context(operation: str, **kwargs: Any) -> Dict[str, Any]:
    """Create standardized error context dictionary.
    
    Args:
        operation: Operation that was being performed.
        **kwargs: Additional context information.
        
    Returns:
        Dictionary containing error context.
    """
    context = {"operation": operation}
    context.update(kwargs)
    return context


def wrap_exception(original_exception: Exception, message: str, 
                  error_class: type = TicketAnalysisError,
                  **context: Any) -> TicketAnalysisError:
    """Wrap an existing exception in a ticket analysis error.
    
    Args:
        original_exception: Original exception to wrap.
        message: New error message.
        error_class: Exception class to use for wrapping.
        **context: Additional context information.
        
    Returns:
        New exception wrapping the original.
    """
    details = create_error_context("exception_wrap", **context)
    details["original_exception"] = str(original_exception)
    details["original_type"] = type(original_exception).__name__
    
    return error_class(message, details)