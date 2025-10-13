"""Comprehensive tests for configuration data models.

This module contains unit tests for all configuration models including
OutputFormat, LogLevel, ReportConfig, AuthConfig, MCPConfig, LoggingConfig,
and ApplicationConfig, covering dataclass instantiation, validation,
conversions, and edge cases.
"""

import pytest
from pathlib import Path
from typing import Dict, Any, List

from ticket_analyzer.models.config import (
    OutputFormat, LogLevel, ReportConfig, AuthConfig, MCPConfig,
    LoggingConfig, ApplicationConfig
)


class TestOutputFormat:
    """Test cases for OutputFormat enum."""
    
    def test_enum_values(self) -> None:
        """Test that all expected output format values exist."""
        expected_values = {"table", "json", "csv", "html", "yaml"}
        actual_values = {fmt.value for fmt in OutputFormat}
        assert actual_values == expected_values
    
    def test_enum_creation_from_string(self) -> None:
        """Test creating OutputFormat from string values."""
        assert OutputFormat("table") == OutputFormat.TABLE
        assert OutputFormat("json") == OutputFormat.JSON
        assert OutputFormat("csv") == OutputFormat.CSV
        assert OutputFormat("html") == OutputFormat.HTML
        assert OutputFormat("yaml") == OutputFormat.YAML
    
    def test_enum_invalid_value(self) -> None:
        """Test that invalid format values raise ValueError."""
        with pytest.raises(ValueError, match="'xml' is not a valid OutputFormat"):
            OutputFormat("xml")
    
    def test_enum_case_sensitivity(self) -> None:
        """Test that enum values are case sensitive."""
        with pytest.raises(ValueError):
            OutputFormat("TABLE")  # uppercase should fail
        
        with pytest.raises(ValueError):
            OutputFormat("Json")  # mixed case should fail


class TestLogLevel:
    """Test cases for LogLevel enum."""
    
    def test_enum_values(self) -> None:
        """Test that all expected log level values exist."""
        expected_values = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        actual_values = {level.value for level in LogLevel}
        assert actual_values == expected_values
    
    def test_enum_creation_from_string(self) -> None:
        """Test creating LogLevel from string values."""
        assert LogLevel("DEBUG") == LogLevel.DEBUG
        assert LogLevel("INFO") == LogLevel.INFO
        assert LogLevel("WARNING") == LogLevel.WARNING
        assert LogLevel("ERROR") == LogLevel.ERROR
        assert LogLevel("CRITICAL") == LogLevel.CRITICAL
    
    def test_enum_invalid_value(self) -> None:
        """Test that invalid log level values raise ValueError."""
        with pytest.raises(ValueError, match="'TRACE' is not a valid LogLevel"):
            LogLevel("TRACE")


class TestReportConfig:
    """Test cases for ReportConfig dataclass."""
    
    def test_default_initialization(self) -> None:
        """Test ReportConfig with default values."""
        config = ReportConfig()
        
        assert config.format == OutputFormat.TABLE
        assert config.output_path is None
        assert config.include_charts is True
        assert config.color_output is True
        assert config.template_name is None
        assert config.sanitize_output is True
        assert config.max_results_display == 100
        assert config.show_progress is True
        assert config.verbose is False
        assert config.theme == "auto"
    
    def test_initialization_with_all_fields(self) -> None:
        """Test ReportConfig with all fields populated."""
        config = ReportConfig(
            format=OutputFormat.JSON,
            output_path="/tmp/report.json",
            include_charts=False,
            color_output=False,
            template_name="custom_template",
            sanitize_output=False,
            max_results_display=500,
            show_progress=False,
            verbose=True,
            theme="dark"
        )
        
        assert config.format == OutputFormat.JSON
        assert config.output_path == "/tmp/report.json"
        assert config.include_charts is False
        assert config.color_output is False
        assert config.template_name == "custom_template"
        assert config.sanitize_output is False
        assert config.max_results_display == 500
        assert config.show_progress is False
        assert config.verbose is True
        assert config.theme == "dark"
    
    def test_validate_success(self) -> None:
        """Test successful validation of ReportConfig."""
        config = ReportConfig(
            max_results_display=1000,
            output_path="/tmp/valid_report.json",
            theme="light"
        )
        
        # Should not raise any exception
        config.validate()
    
    def test_validate_max_results_display_zero(self) -> None:
        """Test validation fails for zero max_results_display."""
        config = ReportConfig(max_results_display=0)
        
        with pytest.raises(ValueError, match="max_results_display must be positive"):
            config.validate()
    
    def test_validate_max_results_display_negative(self) -> None:
        """Test validation fails for negative max_results_display."""
        config = ReportConfig(max_results_display=-1)
        
        with pytest.raises(ValueError, match="max_results_display must be positive"):
            config.validate()
    
    def test_validate_max_results_display_too_large(self) -> None:
        """Test validation fails for max_results_display exceeding limit."""
        config = ReportConfig(max_results_display=10001)
        
        with pytest.raises(ValueError, match="max_results_display cannot exceed 10000"):
            config.validate()
    
    def test_validate_output_path_directory(self, tmp_path: Path) -> None:
        """Test validation fails when output_path is a directory."""
        config = ReportConfig(output_path=str(tmp_path))
        
        with pytest.raises(ValueError, match="output_path cannot be a directory"):
            config.validate()
    
    def test_validate_invalid_theme(self) -> None:
        """Test validation fails for invalid theme."""
        config = ReportConfig(theme="invalid_theme")
        
        with pytest.raises(ValueError, match="theme must be 'light', 'dark', or 'auto'"):
            config.validate()
    
    def test_get_output_extension(self) -> None:
        """Test getting appropriate file extensions for different formats."""
        extensions = {
            OutputFormat.TABLE: ".txt",
            OutputFormat.JSON: ".json",
            OutputFormat.CSV: ".csv",
            OutputFormat.HTML: ".html",
            OutputFormat.YAML: ".yaml"
        }
        
        for format_type, expected_ext in extensions.items():
            config = ReportConfig(format=format_type)
            assert config.get_output_extension() == expected_ext
    
    def test_to_dict_conversion(self) -> None:
        """Test converting ReportConfig to dictionary."""
        config = ReportConfig(
            format=OutputFormat.HTML,
            output_path="/tmp/report.html",
            include_charts=False,
            max_results_display=200,
            theme="dark"
        )
        
        result = config.to_dict()
        
        expected = {
            "format": "html",
            "output_path": "/tmp/report.html",
            "include_charts": False,
            "color_output": True,  # Default value
            "template_name": None,  # Default value
            "sanitize_output": True,  # Default value
            "max_results_display": 200,
            "show_progress": True,  # Default value
            "verbose": False,  # Default value
            "theme": "dark"
        }
        
        assert result == expected


class TestAuthConfig:
    """Test cases for AuthConfig dataclass."""
    
    def test_default_initialization(self) -> None:
        """Test AuthConfig with default values."""
        config = AuthConfig()
        
        assert config.timeout_seconds == 60
        assert config.max_retry_attempts == 3
        assert config.check_interval_seconds == 300
        assert config.session_duration_hours == 8
        assert config.auto_refresh is True
        assert config.require_auth is True
        assert config.auth_method == "midway"
        assert config.cache_credentials is False
    
    def test_initialization_with_all_fields(self) -> None:
        """Test AuthConfig with all fields populated."""
        config = AuthConfig(
            timeout_seconds=120,
            max_retry_attempts=5,
            check_interval_seconds=600,
            session_duration_hours=12,
            auto_refresh=False,
            require_auth=False,
            auth_method="kerberos",
            cache_credentials=True
        )
        
        assert config.timeout_seconds == 120
        assert config.max_retry_attempts == 5
        assert config.check_interval_seconds == 600
        assert config.session_duration_hours == 12
        assert config.auto_refresh is False
        assert config.require_auth is False
        assert config.auth_method == "kerberos"
        assert config.cache_credentials is True
    
    def test_validate_success(self) -> None:
        """Test successful validation of AuthConfig."""
        config = AuthConfig(
            timeout_seconds=30,
            max_retry_attempts=2,
            check_interval_seconds=180,
            session_duration_hours=4,
            auth_method="midway"
        )
        
        # Should not raise any exception
        config.validate()
    
    def test_validate_timeout_seconds_zero(self) -> None:
        """Test validation fails for zero timeout_seconds."""
        config = AuthConfig(timeout_seconds=0)
        
        with pytest.raises(ValueError, match="timeout_seconds must be positive"):
            config.validate()
    
    def test_validate_timeout_seconds_negative(self) -> None:
        """Test validation fails for negative timeout_seconds."""
        config = AuthConfig(timeout_seconds=-1)
        
        with pytest.raises(ValueError, match="timeout_seconds must be positive"):
            config.validate()
    
    def test_validate_timeout_seconds_too_large(self) -> None:
        """Test validation fails for timeout_seconds exceeding limit."""
        config = AuthConfig(timeout_seconds=301)
        
        with pytest.raises(ValueError, match="timeout_seconds cannot exceed 300"):
            config.validate()
    
    def test_validate_max_retry_attempts_negative(self) -> None:
        """Test validation fails for negative max_retry_attempts."""
        config = AuthConfig(max_retry_attempts=-1)
        
        with pytest.raises(ValueError, match="max_retry_attempts cannot be negative"):
            config.validate()
    
    def test_validate_max_retry_attempts_too_large(self) -> None:
        """Test validation fails for max_retry_attempts exceeding limit."""
        config = AuthConfig(max_retry_attempts=11)
        
        with pytest.raises(ValueError, match="max_retry_attempts cannot exceed 10"):
            config.validate()
    
    def test_validate_check_interval_seconds_zero(self) -> None:
        """Test validation fails for zero check_interval_seconds."""
        config = AuthConfig(check_interval_seconds=0)
        
        with pytest.raises(ValueError, match="check_interval_seconds must be positive"):
            config.validate()
    
    def test_validate_session_duration_hours_zero(self) -> None:
        """Test validation fails for zero session_duration_hours."""
        config = AuthConfig(session_duration_hours=0)
        
        with pytest.raises(ValueError, match="session_duration_hours must be positive"):
            config.validate()
    
    def test_validate_session_duration_hours_too_large(self) -> None:
        """Test validation fails for session_duration_hours exceeding limit."""
        config = AuthConfig(session_duration_hours=25)
        
        with pytest.raises(ValueError, match="session_duration_hours cannot exceed 24"):
            config.validate()
    
    def test_validate_invalid_auth_method(self) -> None:
        """Test validation fails for invalid auth_method."""
        config = AuthConfig(auth_method="invalid_method")
        
        with pytest.raises(ValueError, match="auth_method must be 'midway', 'kerberos', or 'none'"):
            config.validate()
    
    def test_to_dict_conversion(self) -> None:
        """Test converting AuthConfig to dictionary."""
        config = AuthConfig(
            timeout_seconds=90,
            max_retry_attempts=4,
            auth_method="kerberos"
        )
        
        result = config.to_dict()
        
        expected = {
            "timeout_seconds": 90,
            "max_retry_attempts": 4,
            "check_interval_seconds": 300,  # Default
            "session_duration_hours": 8,  # Default
            "auto_refresh": True,  # Default
            "require_auth": True,  # Default
            "auth_method": "kerberos",
            "cache_credentials": False  # Default
        }
        
        assert result == expected


class TestMCPConfig:
    """Test cases for MCPConfig dataclass."""
    
    def test_default_initialization(self) -> None:
        """Test MCPConfig with default values."""
        config = MCPConfig()
        
        assert config.server_command == ["node", "mcp-server.js"]
        assert config.connection_timeout == 30
        assert config.request_timeout == 60
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.circuit_breaker_threshold == 5
        assert config.circuit_breaker_timeout == 60
        assert config.enable_logging is False
    
    def test_initialization_with_all_fields(self) -> None:
        """Test MCPConfig with all fields populated."""
        server_command = ["python", "mcp_server.py"]
        
        config = MCPConfig(
            server_command=server_command,
            connection_timeout=45,
            request_timeout=120,
            max_retries=5,
            retry_delay=2.0,
            circuit_breaker_threshold=10,
            circuit_breaker_timeout=120,
            enable_logging=True
        )
        
        assert config.server_command == server_command
        assert config.connection_timeout == 45
        assert config.request_timeout == 120
        assert config.max_retries == 5
        assert config.retry_delay == 2.0
        assert config.circuit_breaker_threshold == 10
        assert config.circuit_breaker_timeout == 120
        assert config.enable_logging is True
    
    def test_validate_success(self) -> None:
        """Test successful validation of MCPConfig."""
        config = MCPConfig(
            server_command=["node", "server.js"],
            connection_timeout=20,
            request_timeout=30,
            max_retries=2,
            retry_delay=0.5,
            circuit_breaker_threshold=3,
            circuit_breaker_timeout=30
        )
        
        # Should not raise any exception
        config.validate()
    
    def test_validate_empty_server_command(self) -> None:
        """Test validation fails for empty server_command."""
        config = MCPConfig(server_command=[])
        
        with pytest.raises(ValueError, match="server_command cannot be empty"):
            config.validate()
    
    def test_validate_connection_timeout_zero(self) -> None:
        """Test validation fails for zero connection_timeout."""
        config = MCPConfig(connection_timeout=0)
        
        with pytest.raises(ValueError, match="connection_timeout must be positive"):
            config.validate()
    
    def test_validate_request_timeout_negative(self) -> None:
        """Test validation fails for negative request_timeout."""
        config = MCPConfig(request_timeout=-1)
        
        with pytest.raises(ValueError, match="request_timeout must be positive"):
            config.validate()
    
    def test_validate_max_retries_negative(self) -> None:
        """Test validation fails for negative max_retries."""
        config = MCPConfig(max_retries=-1)
        
        with pytest.raises(ValueError, match="max_retries cannot be negative"):
            config.validate()
    
    def test_validate_retry_delay_negative(self) -> None:
        """Test validation fails for negative retry_delay."""
        config = MCPConfig(retry_delay=-0.5)
        
        with pytest.raises(ValueError, match="retry_delay cannot be negative"):
            config.validate()
    
    def test_validate_circuit_breaker_threshold_zero(self) -> None:
        """Test validation fails for zero circuit_breaker_threshold."""
        config = MCPConfig(circuit_breaker_threshold=0)
        
        with pytest.raises(ValueError, match="circuit_breaker_threshold must be positive"):
            config.validate()
    
    def test_validate_circuit_breaker_timeout_zero(self) -> None:
        """Test validation fails for zero circuit_breaker_timeout."""
        config = MCPConfig(circuit_breaker_timeout=0)
        
        with pytest.raises(ValueError, match="circuit_breaker_timeout must be positive"):
            config.validate()


class TestLoggingConfig:
    """Test cases for LoggingConfig dataclass."""
    
    def test_default_initialization(self) -> None:
        """Test LoggingConfig with default values."""
        config = LoggingConfig()
        
        assert config.level == LogLevel.INFO
        assert config.format == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        assert config.file_path is None
        assert config.max_file_size == 10 * 1024 * 1024  # 10MB
        assert config.backup_count == 5
        assert config.sanitize_logs is True
        assert config.include_timestamps is True
        assert config.include_caller_info is False
    
    def test_initialization_with_all_fields(self) -> None:
        """Test LoggingConfig with all fields populated."""
        config = LoggingConfig(
            level=LogLevel.DEBUG,
            format="%(levelname)s: %(message)s",
            file_path="/tmp/app.log",
            max_file_size=5 * 1024 * 1024,  # 5MB
            backup_count=3,
            sanitize_logs=False,
            include_timestamps=False,
            include_caller_info=True
        )
        
        assert config.level == LogLevel.DEBUG
        assert config.format == "%(levelname)s: %(message)s"
        assert config.file_path == "/tmp/app.log"
        assert config.max_file_size == 5 * 1024 * 1024
        assert config.backup_count == 3
        assert config.sanitize_logs is False
        assert config.include_timestamps is False
        assert config.include_caller_info is True
    
    def test_validate_success(self) -> None:
        """Test successful validation of LoggingConfig."""
        config = LoggingConfig(
            max_file_size=1024 * 1024,  # 1MB
            backup_count=2,
            file_path="/tmp/valid.log"
        )
        
        # Should not raise any exception
        config.validate()
    
    def test_validate_max_file_size_zero(self) -> None:
        """Test validation fails for zero max_file_size."""
        config = LoggingConfig(max_file_size=0)
        
        with pytest.raises(ValueError, match="max_file_size must be positive"):
            config.validate()
    
    def test_validate_max_file_size_negative(self) -> None:
        """Test validation fails for negative max_file_size."""
        config = LoggingConfig(max_file_size=-1)
        
        with pytest.raises(ValueError, match="max_file_size must be positive"):
            config.validate()
    
    def test_validate_backup_count_negative(self) -> None:
        """Test validation fails for negative backup_count."""
        config = LoggingConfig(backup_count=-1)
        
        with pytest.raises(ValueError, match="backup_count cannot be negative"):
            config.validate()
    
    def test_validate_file_path_directory(self, tmp_path: Path) -> None:
        """Test validation fails when file_path is a directory."""
        config = LoggingConfig(file_path=str(tmp_path))
        
        with pytest.raises(ValueError, match="file_path cannot be a directory"):
            config.validate()


class TestApplicationConfig:
    """Test cases for ApplicationConfig dataclass."""
    
    def test_default_initialization(self) -> None:
        """Test ApplicationConfig with default values."""
        config = ApplicationConfig()
        
        assert isinstance(config.auth, AuthConfig)
        assert isinstance(config.report, ReportConfig)
        assert isinstance(config.mcp, MCPConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert config.data_dir is None
        assert config.config_dir is None
        assert config.cache_dir is None
        assert config.temp_dir is None
        assert config.debug_mode is False
        assert config.max_concurrent_requests == 10
    
    def test_initialization_with_all_fields(self) -> None:
        """Test ApplicationConfig with all fields populated."""
        auth_config = AuthConfig(timeout_seconds=120)
        report_config = ReportConfig(format=OutputFormat.JSON)
        mcp_config = MCPConfig(connection_timeout=45)
        logging_config = LoggingConfig(level=LogLevel.DEBUG)
        
        config = ApplicationConfig(
            auth=auth_config,
            report=report_config,
            mcp=mcp_config,
            logging=logging_config,
            data_dir="/tmp/data",
            config_dir="/tmp/config",
            cache_dir="/tmp/cache",
            temp_dir="/tmp/temp",
            debug_mode=True,
            max_concurrent_requests=20
        )
        
        assert config.auth == auth_config
        assert config.report == report_config
        assert config.mcp == mcp_config
        assert config.logging == logging_config
        assert config.data_dir == "/tmp/data"
        assert config.config_dir == "/tmp/config"
        assert config.cache_dir == "/tmp/cache"
        assert config.temp_dir == "/tmp/temp"
        assert config.debug_mode is True
        assert config.max_concurrent_requests == 20
    
    def test_validate_success(self) -> None:
        """Test successful validation of ApplicationConfig."""
        config = ApplicationConfig(max_concurrent_requests=5)
        
        # Should not raise any exception
        config.validate()
    
    def test_validate_max_concurrent_requests_zero(self) -> None:
        """Test validation fails for zero max_concurrent_requests."""
        config = ApplicationConfig(max_concurrent_requests=0)
        
        with pytest.raises(ValueError, match="max_concurrent_requests must be positive"):
            config.validate()
    
    def test_validate_max_concurrent_requests_too_large(self) -> None:
        """Test validation fails for max_concurrent_requests exceeding limit."""
        config = ApplicationConfig(max_concurrent_requests=101)
        
        with pytest.raises(ValueError, match="max_concurrent_requests cannot exceed 100"):
            config.validate()
    
    def test_validate_propagates_to_subconfigs(self) -> None:
        """Test that validation propagates to sub-configurations."""
        # Create config with invalid auth timeout
        invalid_auth = AuthConfig(timeout_seconds=-1)
        config = ApplicationConfig(auth=invalid_auth)
        
        with pytest.raises(ValueError, match="timeout_seconds must be positive"):
            config.validate()
    
    def test_to_dict_conversion(self) -> None:
        """Test converting ApplicationConfig to dictionary."""
        config = ApplicationConfig(
            debug_mode=True,
            max_concurrent_requests=15
        )
        
        result = config.to_dict()
        
        # Check that all sections are present
        assert "auth" in result
        assert "report" in result
        assert "mcp" in result
        assert "logging" in result
        
        # Check specific values
        assert result["debug_mode"] is True
        assert result["max_concurrent_requests"] == 15
        assert result["data_dir"] is None
        
        # Check that sub-configs are properly converted
        assert isinstance(result["auth"], dict)
        assert isinstance(result["report"], dict)
        assert isinstance(result["mcp"], dict)
        assert isinstance(result["logging"], dict)
    
    def test_from_dict_creation(self) -> None:
        """Test creating ApplicationConfig from dictionary."""
        data = {
            "auth": {
                "timeout_seconds": 90,
                "auth_method": "kerberos"
            },
            "report": {
                "format": "json",
                "max_results_display": 200
            },
            "mcp": {
                "server_command": ["python", "server.py"],
                "connection_timeout": 45
            },
            "logging": {
                "level": "DEBUG",
                "file_path": "/tmp/app.log"
            },
            "debug_mode": True,
            "max_concurrent_requests": 20
        }
        
        config = ApplicationConfig.from_dict(data)
        
        # Check auth config
        assert config.auth.timeout_seconds == 90
        assert config.auth.auth_method == "kerberos"
        
        # Check report config
        assert config.report.format == OutputFormat.JSON
        assert config.report.max_results_display == 200
        
        # Check mcp config
        assert config.mcp.server_command == ["python", "server.py"]
        assert config.mcp.connection_timeout == 45
        
        # Check logging config
        assert config.logging.level == LogLevel.DEBUG
        assert config.logging.file_path == "/tmp/app.log"
        
        # Check other fields
        assert config.debug_mode is True
        assert config.max_concurrent_requests == 20
    
    def test_from_dict_with_partial_data(self) -> None:
        """Test creating ApplicationConfig from dictionary with partial data."""
        data = {
            "auth": {
                "timeout_seconds": 120
            },
            "debug_mode": True
        }
        
        config = ApplicationConfig.from_dict(data)
        
        # Check that provided values are set
        assert config.auth.timeout_seconds == 120
        assert config.debug_mode is True
        
        # Check that other auth values use defaults
        assert config.auth.max_retry_attempts == 3  # Default
        assert config.auth.auth_method == "midway"  # Default
        
        # Check that other configs use defaults
        assert config.report.format == OutputFormat.TABLE  # Default
        assert config.max_concurrent_requests == 10  # Default
    
    def test_from_dict_empty_data(self) -> None:
        """Test creating ApplicationConfig from empty dictionary."""
        config = ApplicationConfig.from_dict({})
        
        # Should create config with all defaults
        assert config.auth.timeout_seconds == 60  # Default
        assert config.report.format == OutputFormat.TABLE  # Default
        assert config.mcp.connection_timeout == 30  # Default
        assert config.logging.level == LogLevel.INFO  # Default
        assert config.debug_mode is False  # Default
        assert config.max_concurrent_requests == 10  # Default
    
    def test_default_subconfig_independence(self) -> None:
        """Test that default sub-configurations are independent instances."""
        config1 = ApplicationConfig()
        config2 = ApplicationConfig()
        
        # Modify one config
        config1.auth.timeout_seconds = 120
        config1.report.max_results_display = 500
        
        # Other config should not be affected
        assert config2.auth.timeout_seconds == 60  # Default
        assert config2.report.max_results_display == 100  # Default
    
    def test_edge_case_very_large_max_concurrent_requests(self) -> None:
        """Test handling of very large max_concurrent_requests."""
        config = ApplicationConfig(max_concurrent_requests=100)  # At the limit
        
        # Should validate successfully
        config.validate()
        
        # But 101 should fail
        config.max_concurrent_requests = 101
        with pytest.raises(ValueError):
            config.validate()
    
    def test_edge_case_zero_values_in_subconfigs(self) -> None:
        """Test handling of zero values in sub-configurations."""
        # This should fail validation due to zero timeout
        config = ApplicationConfig()
        config.auth.timeout_seconds = 0
        
        with pytest.raises(ValueError, match="timeout_seconds must be positive"):
            config.validate()