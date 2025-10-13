"""Configuration handlers implementing Chain of Responsibility pattern.

This module contains specific configuration handlers for different sources:
command-line arguments, configuration files (JSON/INI), environment variables,
and default values. Each handler implements the ConfigurationHandlerInterface
and can be chained together to create a configuration hierarchy.
"""

from __future__ import annotations
import os
import json
import configparser
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from abc import ABC

from ..interfaces import ConfigurationHandlerInterface
from ..models.config import ApplicationConfig, OutputFormat, LogLevel
from ..models.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class BaseConfigurationHandler(ConfigurationHandlerInterface, ABC):
    """Base class for configuration handlers implementing Chain of Responsibility."""
    
    def __init__(self) -> None:
        self._next_handler: Optional[ConfigurationHandlerInterface] = None
    
    def set_next(self, handler: ConfigurationHandlerInterface) -> ConfigurationHandlerInterface:
        """Set the next handler in the chain.
        
        Args:
            handler: Next handler in the chain.
            
        Returns:
            The handler that was set as next.
        """
        self._next_handler = handler
        return handler
    
    def handle(self, key: str) -> Optional[Any]:
        """Handle configuration request for a specific key.
        
        Args:
            key: Configuration key to retrieve.
            
        Returns:
            Configuration value if found, None otherwise.
        """
        # Try to get value from this handler
        try:
            config = self.load_all()
            if config and key in config:
                return config[key]
        except Exception as e:
            logger.debug(f"Handler {self.__class__.__name__} failed for key '{key}': {e}")
        
        # Pass to next handler if available
        if self._next_handler:
            return self._next_handler.handle(key)
        
        return None


class CommandLineConfigHandler(BaseConfigurationHandler):
    """Handler for command-line arguments configuration.
    
    This handler processes command-line arguments that have been parsed
    and stored in a global registry or passed during initialization.
    It has the highest priority in the configuration hierarchy.
    """
    
    def __init__(self, cli_args: Optional[Dict[str, Any]] = None) -> None:
        """Initialize command-line configuration handler.
        
        Args:
            cli_args: Dictionary of parsed command-line arguments.
        """
        super().__init__()
        self._cli_args = cli_args or {}
        self._source_type = "cli"
    
    def set_cli_args(self, cli_args: Dict[str, Any]) -> None:
        """Set command-line arguments.
        
        Args:
            cli_args: Dictionary of parsed CLI arguments.
        """
        self._cli_args = cli_args
    
    def load_all(self) -> Dict[str, Any]:
        """Load all configuration from command-line arguments.
        
        Returns:
            Dictionary containing CLI configuration.
        """
        if not self._cli_args:
            return {}
        
        # Convert CLI arguments to configuration structure
        config = {}
        
        # Map CLI arguments to configuration keys
        cli_mapping = {
            'format': 'report.format',
            'output': 'report.output_path',
            'verbose': 'report.verbose',
            'color': 'report.color_output',
            'max_results': 'report.max_results_display',
            'timeout': 'auth.timeout_seconds',
            'retry_attempts': 'auth.max_retry_attempts',
            'debug': 'debug_mode',
            'config_file': '_config_file_override'
        }
        
        for cli_key, config_key in cli_mapping.items():
            if cli_key in self._cli_args:
                value = self._cli_args[cli_key]
                if value is not None:
                    self._set_nested_config(config, config_key, value)
        
        return config
    
    def _set_nested_config(self, config: Dict[str, Any], key: str, value: Any) -> None:
        """Set nested configuration value using dot notation.
        
        Args:
            config: Configuration dictionary to modify.
            key: Key with dot notation.
            value: Value to set.
        """
        keys = key.split('.')
        current = config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def can_handle_source(self, source_type: str) -> bool:
        """Check if handler can process the configuration source type.
        
        Args:
            source_type: Type of configuration source.
            
        Returns:
            True if handler can process CLI sources.
        """
        return source_type == "cli"


class FileConfigHandler(BaseConfigurationHandler):
    """Handler for configuration files (JSON and INI formats).
    
    This handler loads configuration from JSON and INI files in the
    specified configuration directory. It supports multiple file formats
    and provides detailed error reporting for malformed files.
    """
    
    def __init__(self, config_dir: Path) -> None:
        """Initialize file configuration handler.
        
        Args:
            config_dir: Directory containing configuration files.
        """
        super().__init__()
        self._config_dir = config_dir
        self._source_type = "file"
        
        # Configuration file names in order of preference
        self._config_files = [
            "config.json",
            "config.ini",
            ".ticket-analyzer.json",
            ".ticket-analyzer.ini"
        ]
    
    def load_all(self) -> Dict[str, Any]:
        """Load all configuration from files.
        
        Returns:
            Dictionary containing file configuration.
            
        Raises:
            ConfigurationError: If file parsing fails.
        """
        config = {}
        
        for filename in self._config_files:
            file_path = self._config_dir / filename
            if file_path.exists():
                try:
                    file_config = self._load_config_file(file_path)
                    if file_config:
                        # Merge with existing config (later files override earlier ones)
                        config.update(file_config)
                        logger.debug(f"Loaded configuration from {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to load config from {file_path}: {e}")
                    continue
        
        return config
    
    def _load_config_file(self, file_path: Path) -> Dict[str, Any]:
        """Load configuration from a specific file.
        
        Args:
            file_path: Path to configuration file.
            
        Returns:
            Dictionary containing file configuration.
            
        Raises:
            ConfigurationError: If file format is unsupported or parsing fails.
        """
        suffix = file_path.suffix.lower()
        
        if suffix == '.json':
            return self._load_json_config(file_path)
        elif suffix == '.ini':
            return self._load_ini_config(file_path)
        else:
            raise ConfigurationError(f"Unsupported configuration file format: {suffix}")
    
    def _load_json_config(self, file_path: Path) -> Dict[str, Any]:
        """Load JSON configuration file.
        
        Args:
            file_path: Path to JSON file.
            
        Returns:
            Dictionary containing JSON configuration.
            
        Raises:
            ConfigurationError: If JSON parsing fails.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if not isinstance(config, dict):
                raise ConfigurationError(f"JSON config must be an object, got {type(config)}")
            
            return config
            
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to read JSON config {file_path}: {e}")
    
    def _load_ini_config(self, file_path: Path) -> Dict[str, Any]:
        """Load INI configuration file.
        
        Args:
            file_path: Path to INI file.
            
        Returns:
            Dictionary containing INI configuration.
            
        Raises:
            ConfigurationError: If INI parsing fails.
        """
        try:
            parser = configparser.ConfigParser()
            parser.read(file_path, encoding='utf-8')
            
            config = {}
            
            for section_name in parser.sections():
                section_config = {}
                
                for key, value in parser[section_name].items():
                    # Convert string values to appropriate types
                    section_config[key] = self._convert_ini_value(value)
                
                config[section_name] = section_config
            
            return config
            
        except configparser.Error as e:
            raise ConfigurationError(f"Invalid INI format in {file_path}: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to read INI config {file_path}: {e}")
    
    def _convert_ini_value(self, value: str) -> Any:
        """Convert INI string value to appropriate Python type.
        
        Args:
            value: String value from INI file.
            
        Returns:
            Converted value (bool, int, float, or string).
        """
        # Handle boolean values
        if value.lower() in ('true', 'yes', '1', 'on'):
            return True
        elif value.lower() in ('false', 'no', '0', 'off'):
            return False
        
        # Handle numeric values
        try:
            # Try integer first
            if '.' not in value:
                return int(value)
            else:
                return float(value)
        except ValueError:
            pass
        
        # Handle lists (comma-separated values)
        if ',' in value:
            return [item.strip() for item in value.split(',')]
        
        # Return as string
        return value
    
    def can_handle_source(self, source_type: str) -> bool:
        """Check if handler can process the configuration source type.
        
        Args:
            source_type: Type of configuration source.
            
        Returns:
            True if handler can process file sources.
        """
        return source_type == "file"


class EnvironmentConfigHandler(BaseConfigurationHandler):
    """Handler for environment variable configuration.
    
    This handler loads configuration from environment variables with
    a specific prefix (TICKET_ANALYZER_). It supports nested configuration
    by using double underscores as separators.
    """
    
    def __init__(self, prefix: str = "TICKET_ANALYZER_") -> None:
        """Initialize environment variable configuration handler.
        
        Args:
            prefix: Prefix for environment variables.
        """
        super().__init__()
        self._prefix = prefix
        self._source_type = "environment"
    
    def load_all(self) -> Dict[str, Any]:
        """Load all configuration from environment variables.
        
        Returns:
            Dictionary containing environment configuration.
        """
        config = {}
        
        for key, value in os.environ.items():
            if key.startswith(self._prefix):
                # Remove prefix and convert to config key
                config_key = key[len(self._prefix):].lower()
                
                # Convert double underscores to dots for nested keys
                config_key = config_key.replace('__', '.')
                
                # Convert value to appropriate type
                converted_value = self._convert_env_value(value)
                
                # Set nested configuration
                self._set_nested_config(config, config_key, converted_value)
        
        return config
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type.
        
        Args:
            value: Environment variable value.
            
        Returns:
            Converted value.
        """
        # Handle boolean values
        if value.lower() in ('true', 'yes', '1'):
            return True
        elif value.lower() in ('false', 'no', '0'):
            return False
        
        # Handle numeric values
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # Handle JSON values
        if value.startswith(('{', '[', '"')):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        # Handle comma-separated lists
        if ',' in value:
            return [item.strip() for item in value.split(',')]
        
        return value
    
    def _set_nested_config(self, config: Dict[str, Any], key: str, value: Any) -> None:
        """Set nested configuration value using dot notation.
        
        Args:
            config: Configuration dictionary to modify.
            key: Key with dot notation.
            value: Value to set.
        """
        keys = key.split('.')
        current = config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def can_handle_source(self, source_type: str) -> bool:
        """Check if handler can process the configuration source type.
        
        Args:
            source_type: Type of configuration source.
            
        Returns:
            True if handler can process environment sources.
        """
        return source_type == "environment"


class DefaultConfigHandler(BaseConfigurationHandler):
    """Handler for default configuration values.
    
    This handler provides default values for all configuration options.
    It has the lowest priority in the configuration hierarchy and serves
    as a fallback when no other source provides a value.
    """
    
    def __init__(self) -> None:
        """Initialize default configuration handler."""
        super().__init__()
        self._source_type = "default"
        self._defaults = self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration dictionary.
        
        Returns:
            Dictionary containing default configuration values.
        """
        # Create default ApplicationConfig and convert to dict
        default_app_config = ApplicationConfig()
        return default_app_config.to_dict()
    
    def load_all(self) -> Dict[str, Any]:
        """Load all default configuration values.
        
        Returns:
            Dictionary containing default configuration.
        """
        return self._defaults.copy()
    
    def can_handle_source(self, source_type: str) -> bool:
        """Check if handler can process the configuration source type.
        
        Args:
            source_type: Type of configuration source.
            
        Returns:
            True if handler can process default sources.
        """
        return source_type == "default"


class ConfigurationValidator:
    """Validator for configuration settings with schema validation."""
    
    def __init__(self) -> None:
        """Initialize configuration validator."""
        self._schema = self._create_validation_schema()
    
    def _create_validation_schema(self) -> Dict[str, Any]:
        """Create validation schema for configuration.
        
        Returns:
            Dictionary representing the configuration schema.
        """
        return {
            "auth": {
                "timeout_seconds": {"type": int, "min": 1, "max": 300},
                "max_retry_attempts": {"type": int, "min": 0, "max": 10},
                "check_interval_seconds": {"type": int, "min": 1},
                "session_duration_hours": {"type": int, "min": 1, "max": 24},
                "auto_refresh": {"type": bool},
                "require_auth": {"type": bool},
                "auth_method": {"type": str, "choices": ["midway", "kerberos", "none"]},
                "cache_credentials": {"type": bool}
            },
            "report": {
                "format": {"type": str, "choices": ["table", "json", "csv", "html", "yaml"]},
                "output_path": {"type": str, "optional": True},
                "include_charts": {"type": bool},
                "color_output": {"type": bool},
                "template_name": {"type": str, "optional": True},
                "sanitize_output": {"type": bool},
                "max_results_display": {"type": int, "min": 1, "max": 10000},
                "show_progress": {"type": bool},
                "verbose": {"type": bool},
                "theme": {"type": str, "choices": ["light", "dark", "auto"]}
            },
            "mcp": {
                "server_command": {"type": list},
                "connection_timeout": {"type": int, "min": 1},
                "request_timeout": {"type": int, "min": 1},
                "max_retries": {"type": int, "min": 0},
                "retry_delay": {"type": float, "min": 0},
                "circuit_breaker_threshold": {"type": int, "min": 1},
                "circuit_breaker_timeout": {"type": int, "min": 1},
                "enable_logging": {"type": bool}
            },
            "logging": {
                "level": {"type": str, "choices": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
                "format": {"type": str},
                "file_path": {"type": str, "optional": True},
                "max_file_size": {"type": int, "min": 1},
                "backup_count": {"type": int, "min": 0},
                "sanitize_logs": {"type": bool},
                "include_timestamps": {"type": bool},
                "include_caller_info": {"type": bool}
            },
            "debug_mode": {"type": bool},
            "max_concurrent_requests": {"type": int, "min": 1, "max": 100}
        }
    
    def validate_setting(self, key: str, value: Any) -> bool:
        """Validate a single configuration setting.
        
        Args:
            key: Configuration key.
            value: Value to validate.
            
        Returns:
            True if setting is valid.
            
        Raises:
            ConfigurationError: If validation fails.
        """
        schema = self._get_schema_for_key(key)
        if not schema:
            return True  # No schema defined, assume valid
        
        return self._validate_value(value, schema, key)
    
    def validate_schema(self, config: Dict[str, Any]) -> bool:
        """Validate entire configuration against schema.
        
        Args:
            config: Configuration dictionary to validate.
            
        Returns:
            True if configuration is valid.
            
        Raises:
            ConfigurationError: If validation fails.
        """
        errors = self.get_validation_errors(config)
        if errors:
            raise ConfigurationError(f"Configuration validation failed: {'; '.join(errors)}")
        return True
    
    def get_validation_errors(self, config: Dict[str, Any]) -> List[str]:
        """Get list of validation errors for configuration.
        
        Args:
            config: Configuration dictionary to validate.
            
        Returns:
            List of validation error messages.
        """
        errors = []
        self._validate_recursive(config, self._schema, "", errors)
        return errors
    
    def _validate_recursive(self, config: Dict[str, Any], schema: Dict[str, Any], 
                          prefix: str, errors: List[str]) -> None:
        """Recursively validate configuration against schema.
        
        Args:
            config: Configuration to validate.
            schema: Schema to validate against.
            prefix: Key prefix for error messages.
            errors: List to collect error messages.
        """
        for key, value in config.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if key in schema:
                schema_def = schema[key]
                
                if isinstance(schema_def, dict) and "type" in schema_def:
                    # Leaf node with validation rules
                    try:
                        self._validate_value(value, schema_def, full_key)
                    except ConfigurationError as e:
                        errors.append(str(e))
                elif isinstance(schema_def, dict):
                    # Nested object
                    if isinstance(value, dict):
                        self._validate_recursive(value, schema_def, full_key, errors)
                    else:
                        errors.append(f"'{full_key}' must be an object, got {type(value).__name__}")
    
    def _validate_value(self, value: Any, schema_def: Dict[str, Any], key: str) -> bool:
        """Validate a single value against schema definition.
        
        Args:
            value: Value to validate.
            schema_def: Schema definition for the value.
            key: Configuration key for error messages.
            
        Returns:
            True if value is valid.
            
        Raises:
            ConfigurationError: If validation fails.
        """
        # Check if optional and None
        if schema_def.get("optional", False) and value is None:
            return True
        
        # Check type
        expected_type = schema_def["type"]
        if not isinstance(value, expected_type):
            raise ConfigurationError(
                f"'{key}' must be of type {expected_type.__name__}, got {type(value).__name__}"
            )
        
        # Check choices
        if "choices" in schema_def:
            if value not in schema_def["choices"]:
                raise ConfigurationError(
                    f"'{key}' must be one of {schema_def['choices']}, got '{value}'"
                )
        
        # Check numeric constraints
        if isinstance(value, (int, float)):
            if "min" in schema_def and value < schema_def["min"]:
                raise ConfigurationError(
                    f"'{key}' must be >= {schema_def['min']}, got {value}"
                )
            if "max" in schema_def and value > schema_def["max"]:
                raise ConfigurationError(
                    f"'{key}' must be <= {schema_def['max']}, got {value}"
                )
        
        return True
    
    def _get_schema_for_key(self, key: str) -> Optional[Dict[str, Any]]:
        """Get schema definition for a specific key.
        
        Args:
            key: Configuration key with dot notation.
            
        Returns:
            Schema definition or None if not found.
        """
        keys = key.split('.')
        current = self._schema
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None
        
        return current if isinstance(current, dict) else None
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the configuration schema.
        
        Returns:
            Dictionary representing the configuration schema.
        """
        return self._schema.copy()