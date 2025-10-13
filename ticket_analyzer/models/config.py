"""Configuration models for application settings.

This module contains data models for various configuration aspects of the
ticket analyzer application, including report generation, authentication,
and general application settings.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
from enum import Enum


class OutputFormat(Enum):
    """Supported output formats for reports."""
    TABLE = "table"
    JSON = "json"
    CSV = "csv"
    HTML = "html"
    YAML = "yaml"


class LogLevel(Enum):
    """Supported logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class ReportConfig:
    """Configuration for report generation.
    
    Defines how reports should be generated and formatted, including
    output format, styling options, and content preferences.
    
    Attributes:
        format: Output format for the report
        output_path: File path where report should be saved
        include_charts: Whether to include charts in HTML reports
        color_output: Whether to use color in CLI output
        template_name: Custom template name for HTML reports
        sanitize_output: Whether to sanitize sensitive data in output
        max_results_display: Maximum number of results to display
        show_progress: Whether to show progress indicators
        verbose: Whether to include verbose details
        theme: Color theme for reports ('light', 'dark', 'auto')
    """
    format: OutputFormat = OutputFormat.TABLE
    output_path: Optional[str] = None
    include_charts: bool = True
    color_output: bool = True
    template_name: Optional[str] = None
    sanitize_output: bool = True
    max_results_display: int = 100
    show_progress: bool = True
    verbose: bool = False
    theme: str = "auto"
    
    def validate(self) -> None:
        """Validate report configuration.
        
        Raises:
            ValueError: If configuration values are invalid.
        """
        if self.max_results_display <= 0:
            raise ValueError("max_results_display must be positive")
        
        if self.max_results_display > 10000:
            raise ValueError("max_results_display cannot exceed 10000")
        
        if self.output_path:
            output_path = Path(self.output_path)
            if output_path.exists() and output_path.is_dir():
                raise ValueError("output_path cannot be a directory")
        
        if self.theme not in ["light", "dark", "auto"]:
            raise ValueError("theme must be 'light', 'dark', or 'auto'")
    
    def get_output_extension(self) -> str:
        """Get the appropriate file extension for the output format.
        
        Returns:
            File extension including the dot (e.g., '.json', '.html').
        """
        extension_map = {
            OutputFormat.TABLE: ".txt",
            OutputFormat.JSON: ".json",
            OutputFormat.CSV: ".csv",
            OutputFormat.HTML: ".html",
            OutputFormat.YAML: ".yaml"
        }
        return extension_map.get(self.format, ".txt")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.
        
        Returns:
            Dictionary representation of the configuration.
        """
        return {
            "format": self.format.value,
            "output_path": self.output_path,
            "include_charts": self.include_charts,
            "color_output": self.color_output,
            "template_name": self.template_name,
            "sanitize_output": self.sanitize_output,
            "max_results_display": self.max_results_display,
            "show_progress": self.show_progress,
            "verbose": self.verbose,
            "theme": self.theme
        }


@dataclass
class AuthConfig:
    """Configuration for authentication settings.
    
    Defines authentication behavior including timeouts, retry logic,
    and session management parameters.
    
    Attributes:
        timeout_seconds: Maximum time to wait for authentication
        max_retry_attempts: Number of retry attempts for failed auth
        check_interval_seconds: How often to check auth status
        session_duration_hours: How long auth sessions remain valid
        auto_refresh: Whether to automatically refresh expired sessions
        require_auth: Whether authentication is required
        auth_method: Authentication method to use
        cache_credentials: Whether to cache authentication state
    """
    timeout_seconds: int = 60
    max_retry_attempts: int = 3
    check_interval_seconds: int = 300  # 5 minutes
    session_duration_hours: int = 8
    auto_refresh: bool = True
    require_auth: bool = True
    auth_method: str = "midway"
    cache_credentials: bool = False
    
    def validate(self) -> None:
        """Validate authentication configuration.
        
        Raises:
            ValueError: If configuration values are invalid.
        """
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        
        if self.timeout_seconds > 300:  # 5 minutes max
            raise ValueError("timeout_seconds cannot exceed 300")
        
        if self.max_retry_attempts < 0:
            raise ValueError("max_retry_attempts cannot be negative")
        
        if self.max_retry_attempts > 10:
            raise ValueError("max_retry_attempts cannot exceed 10")
        
        if self.check_interval_seconds <= 0:
            raise ValueError("check_interval_seconds must be positive")
        
        if self.session_duration_hours <= 0:
            raise ValueError("session_duration_hours must be positive")
        
        if self.session_duration_hours > 24:
            raise ValueError("session_duration_hours cannot exceed 24")
        
        if self.auth_method not in ["midway", "kerberos", "none"]:
            raise ValueError("auth_method must be 'midway', 'kerberos', or 'none'")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.
        
        Returns:
            Dictionary representation of the configuration.
        """
        return {
            "timeout_seconds": self.timeout_seconds,
            "max_retry_attempts": self.max_retry_attempts,
            "check_interval_seconds": self.check_interval_seconds,
            "session_duration_hours": self.session_duration_hours,
            "auto_refresh": self.auto_refresh,
            "require_auth": self.require_auth,
            "auth_method": self.auth_method,
            "cache_credentials": self.cache_credentials
        }


@dataclass
class MCPConfig:
    """Configuration for MCP (Model Context Protocol) integration.
    
    Attributes:
        server_command: Command to start MCP server
        connection_timeout: Timeout for MCP connections
        request_timeout: Timeout for individual MCP requests
        max_retries: Maximum number of retry attempts
        retry_delay: Base delay between retries in seconds
        circuit_breaker_threshold: Failure threshold for circuit breaker
        circuit_breaker_timeout: Circuit breaker timeout in seconds
        enable_logging: Whether to enable MCP request/response logging
    """
    server_command: List[str] = field(default_factory=lambda: ["node", "mcp-server.js"])
    connection_timeout: int = 30
    request_timeout: int = 60
    max_retries: int = 3
    retry_delay: float = 1.0
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60
    enable_logging: bool = False
    
    def validate(self) -> None:
        """Validate MCP configuration.
        
        Raises:
            ValueError: If configuration values are invalid.
        """
        if not self.server_command:
            raise ValueError("server_command cannot be empty")
        
        if self.connection_timeout <= 0:
            raise ValueError("connection_timeout must be positive")
        
        if self.request_timeout <= 0:
            raise ValueError("request_timeout must be positive")
        
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        
        if self.retry_delay < 0:
            raise ValueError("retry_delay cannot be negative")
        
        if self.circuit_breaker_threshold <= 0:
            raise ValueError("circuit_breaker_threshold must be positive")
        
        if self.circuit_breaker_timeout <= 0:
            raise ValueError("circuit_breaker_timeout must be positive")


@dataclass
class LoggingConfig:
    """Configuration for application logging.
    
    Attributes:
        level: Logging level
        format: Log message format string
        file_path: Path to log file (None for console only)
        max_file_size: Maximum log file size in bytes
        backup_count: Number of backup log files to keep
        sanitize_logs: Whether to sanitize sensitive data in logs
        include_timestamps: Whether to include timestamps in logs
        include_caller_info: Whether to include caller information
    """
    level: LogLevel = LogLevel.INFO
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    sanitize_logs: bool = True
    include_timestamps: bool = True
    include_caller_info: bool = False
    
    def validate(self) -> None:
        """Validate logging configuration.
        
        Raises:
            ValueError: If configuration values are invalid.
        """
        if self.max_file_size <= 0:
            raise ValueError("max_file_size must be positive")
        
        if self.backup_count < 0:
            raise ValueError("backup_count cannot be negative")
        
        if self.file_path:
            log_path = Path(self.file_path)
            if log_path.exists() and log_path.is_dir():
                raise ValueError("file_path cannot be a directory")


@dataclass
class ApplicationConfig:
    """Main application configuration container.
    
    Contains all configuration sections for the application including
    authentication, reporting, MCP integration, and logging settings.
    
    Attributes:
        auth: Authentication configuration
        report: Report generation configuration
        mcp: MCP integration configuration
        logging: Logging configuration
        data_dir: Directory for application data
        config_dir: Directory for configuration files
        cache_dir: Directory for cache files
        temp_dir: Directory for temporary files
        debug_mode: Whether debug mode is enabled
        max_concurrent_requests: Maximum concurrent API requests
    """
    auth: AuthConfig = field(default_factory=AuthConfig)
    report: ReportConfig = field(default_factory=ReportConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    data_dir: Optional[str] = None
    config_dir: Optional[str] = None
    cache_dir: Optional[str] = None
    temp_dir: Optional[str] = None
    debug_mode: bool = False
    max_concurrent_requests: int = 10
    
    def validate(self) -> None:
        """Validate all configuration sections.
        
        Raises:
            ValueError: If any configuration section is invalid.
        """
        self.auth.validate()
        self.report.validate()
        self.mcp.validate()
        self.logging.validate()
        
        if self.max_concurrent_requests <= 0:
            raise ValueError("max_concurrent_requests must be positive")
        
        if self.max_concurrent_requests > 100:
            raise ValueError("max_concurrent_requests cannot exceed 100")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.
        
        Returns:
            Dictionary representation of the entire configuration.
        """
        return {
            "auth": self.auth.to_dict(),
            "report": self.report.to_dict(),
            "mcp": {
                "server_command": self.mcp.server_command,
                "connection_timeout": self.mcp.connection_timeout,
                "request_timeout": self.mcp.request_timeout,
                "max_retries": self.mcp.max_retries,
                "retry_delay": self.mcp.retry_delay,
                "circuit_breaker_threshold": self.mcp.circuit_breaker_threshold,
                "circuit_breaker_timeout": self.mcp.circuit_breaker_timeout,
                "enable_logging": self.mcp.enable_logging
            },
            "logging": {
                "level": self.logging.level.value,
                "format": self.logging.format,
                "file_path": self.logging.file_path,
                "max_file_size": self.logging.max_file_size,
                "backup_count": self.logging.backup_count,
                "sanitize_logs": self.logging.sanitize_logs,
                "include_timestamps": self.logging.include_timestamps,
                "include_caller_info": self.logging.include_caller_info
            },
            "data_dir": self.data_dir,
            "config_dir": self.config_dir,
            "cache_dir": self.cache_dir,
            "temp_dir": self.temp_dir,
            "debug_mode": self.debug_mode,
            "max_concurrent_requests": self.max_concurrent_requests
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ApplicationConfig:
        """Create configuration from dictionary.
        
        Args:
            data: Dictionary containing configuration data.
            
        Returns:
            New ApplicationConfig instance.
        """
        config = cls()
        
        if "auth" in data:
            auth_data = data["auth"]
            config.auth = AuthConfig(**auth_data)
        
        if "report" in data:
            report_data = data["report"]
            if "format" in report_data:
                report_data["format"] = OutputFormat(report_data["format"])
            config.report = ReportConfig(**report_data)
        
        if "mcp" in data:
            mcp_data = data["mcp"]
            config.mcp = MCPConfig(**mcp_data)
        
        if "logging" in data:
            logging_data = data["logging"]
            if "level" in logging_data:
                logging_data["level"] = LogLevel(logging_data["level"])
            config.logging = LoggingConfig(**logging_data)
        
        # Set other attributes
        for attr in ["data_dir", "config_dir", "cache_dir", "temp_dir", 
                     "debug_mode", "max_concurrent_requests"]:
            if attr in data:
                setattr(config, attr, data[attr])
        
        return config