"""Configuration manager with Chain of Responsibility pattern.

This module implements a hierarchical configuration management system that
supports multiple configuration sources with proper precedence handling.
The configuration hierarchy follows: CLI args > config files > env vars > defaults.
"""

from __future__ import annotations
import os
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

from ..interfaces import (
    ConfigurationInterface,
    ConfigurationHandlerInterface,
    ConfigurationValidatorInterface
)
from ..models.config import ApplicationConfig
from ..models.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class ConfigurationManager(ConfigurationInterface):
    """Main configuration manager implementing Chain of Responsibility pattern.
    
    Manages configuration from multiple sources with proper precedence:
    1. Command-line arguments (highest priority)
    2. Configuration files (JSON/INI)
    3. Environment variables
    4. Default values (lowest priority)
    
    The manager validates all configuration and provides a unified interface
    for accessing settings throughout the application.
    """
    
    def __init__(self, config_dir: Optional[Path] = None) -> None:
        """Initialize configuration manager.
        
        Args:
            config_dir: Directory containing configuration files.
                       Defaults to ~/.ticket-analyzer/
        """
        self._config_dir = config_dir or Path.home() / ".ticket-analyzer"
        self._config_chain: Optional[ConfigurationHandlerInterface] = None
        self._validator: Optional[ConfigurationValidatorInterface] = None
        self._cached_config: Optional[Dict[str, Any]] = None
        self._config_sources: List[str] = []
        
        # Ensure config directory exists
        self._config_dir.mkdir(mode=0o700, exist_ok=True)
        
        # Initialize the configuration chain
        self._setup_configuration_chain()
    
    def _setup_configuration_chain(self) -> None:
        """Set up the Chain of Responsibility for configuration sources."""
        from .handlers import (
            CommandLineConfigHandler,
            FileConfigHandler,
            EnvironmentConfigHandler,
            DefaultConfigHandler
        )
        
        # Create handlers in reverse order of priority
        default_handler = DefaultConfigHandler()
        env_handler = EnvironmentConfigHandler()
        file_handler = FileConfigHandler(self._config_dir)
        cli_handler = CommandLineConfigHandler()
        
        # Chain them together (CLI -> File -> Env -> Default)
        cli_handler.set_next(file_handler)
        file_handler.set_next(env_handler)
        env_handler.set_next(default_handler)
        
        self._config_chain = cli_handler
        
        # Track source order for debugging
        self._config_sources = ["cli", "file", "environment", "default"]
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from all sources with proper precedence.
        
        Returns:
            Dictionary containing merged configuration from all sources.
            
        Raises:
            ConfigurationError: If configuration loading or validation fails.
        """
        if self._cached_config is not None:
            return self._cached_config.copy()
        
        try:
            # Load configuration from each source in the chain
            merged_config = {}
            
            if self._config_chain:
                # Get all configuration from the chain
                merged_config = self._merge_configuration_sources()
            
            # Validate the merged configuration
            if self._validator:
                if not self._validator.validate_schema(merged_config):
                    errors = self._validator.get_validation_errors(merged_config)
                    raise ConfigurationError(
                        f"Configuration validation failed: {'; '.join(errors)}"
                    )
            
            # Cache the validated configuration
            self._cached_config = merged_config
            
            logger.info(f"Configuration loaded successfully from sources: {self._config_sources}")
            return merged_config.copy()
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(f"Configuration loading failed: {e}")
    
    def _merge_configuration_sources(self) -> Dict[str, Any]:
        """Merge configuration from all sources in the chain.
        
        Returns:
            Merged configuration dictionary.
        """
        merged = {}
        
        # Start with defaults and work up the priority chain
        handlers = self._get_all_handlers()
        
        for handler in reversed(handlers):  # Reverse to start with lowest priority
            try:
                handler_config = handler.load_all()
                if handler_config:
                    merged = self._deep_merge_dicts(merged, handler_config)
                    logger.debug(f"Merged config from {handler.__class__.__name__}")
            except Exception as e:
                logger.warning(f"Failed to load config from {handler.__class__.__name__}: {e}")
                continue
        
        return merged
    
    def _get_all_handlers(self) -> List[ConfigurationHandlerInterface]:
        """Get all handlers in the chain.
        
        Returns:
            List of all configuration handlers.
        """
        handlers = []
        current = self._config_chain
        
        while current:
            handlers.append(current)
            current = getattr(current, '_next_handler', None)
        
        return handlers
    
    def _deep_merge_dicts(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries with override taking precedence.
        
        Args:
            base: Base dictionary.
            override: Override dictionary (higher priority).
            
        Returns:
            Merged dictionary.
        """
        result = base.copy()
        
        for key, value in override.items():
            if (key in result and 
                isinstance(result[key], dict) and 
                isinstance(value, dict)):
                # Recursively merge nested dictionaries
                result[key] = self._deep_merge_dicts(result[key], value)
            else:
                # Override the value
                result[key] = value
        
        return result
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a specific configuration setting.
        
        Args:
            key: Configuration key (supports dot notation for nested keys).
            default: Default value if key not found.
            
        Returns:
            Configuration value or default.
        """
        try:
            config = self.load_config()
            return self._get_nested_value(config, key, default)
        except ConfigurationError:
            logger.warning(f"Failed to get setting '{key}', using default: {default}")
            return default
    
    def _get_nested_value(self, config: Dict[str, Any], key: str, default: Any) -> Any:
        """Get value from nested dictionary using dot notation.
        
        Args:
            config: Configuration dictionary.
            key: Key with dot notation (e.g., 'auth.timeout_seconds').
            default: Default value if key not found.
            
        Returns:
            Value from nested dictionary or default.
        """
        keys = key.split('.')
        current = config
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        
        return current
    
    def set_setting(self, key: str, value: Any) -> None:
        """Set a configuration setting.
        
        Args:
            key: Configuration key (supports dot notation).
            value: Value to set.
            
        Raises:
            ConfigurationError: If setting cannot be updated.
        """
        try:
            config = self.load_config()
            self._set_nested_value(config, key, value)
            
            # Invalidate cache to force reload
            self._cached_config = None
            
            logger.debug(f"Setting '{key}' updated to: {value}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to set setting '{key}': {e}")
    
    def _set_nested_value(self, config: Dict[str, Any], key: str, value: Any) -> None:
        """Set value in nested dictionary using dot notation.
        
        Args:
            config: Configuration dictionary to modify.
            key: Key with dot notation.
            value: Value to set.
        """
        keys = key.split('.')
        current = config
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            elif not isinstance(current[k], dict):
                raise ConfigurationError(f"Cannot set nested key '{key}': '{k}' is not a dictionary")
            current = current[k]
        
        # Set the final value
        current[keys[-1]] = value
    
    def has_setting(self, key: str) -> bool:
        """Check if a configuration setting exists.
        
        Args:
            key: Configuration key to check.
            
        Returns:
            True if setting exists, False otherwise.
        """
        try:
            config = self.load_config()
            return self._has_nested_key(config, key)
        except ConfigurationError:
            return False
    
    def _has_nested_key(self, config: Dict[str, Any], key: str) -> bool:
        """Check if nested key exists in dictionary.
        
        Args:
            config: Configuration dictionary.
            key: Key with dot notation.
            
        Returns:
            True if key exists, False otherwise.
        """
        keys = key.split('.')
        current = config
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return False
        
        return True
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all configuration settings.
        
        Returns:
            Dictionary containing all configuration settings.
        """
        return self.load_config()
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration settings.
        
        Args:
            config: Configuration dictionary to validate.
            
        Returns:
            True if configuration is valid, False otherwise.
            
        Raises:
            ConfigurationError: If validation fails with details.
        """
        if not self._validator:
            # If no validator is set, perform basic validation
            return self._basic_validation(config)
        
        return self._validator.validate_schema(config)
    
    def _basic_validation(self, config: Dict[str, Any]) -> bool:
        """Perform basic configuration validation.
        
        Args:
            config: Configuration to validate.
            
        Returns:
            True if basic validation passes.
            
        Raises:
            ConfigurationError: If validation fails.
        """
        try:
            # Try to create ApplicationConfig from the dictionary
            app_config = ApplicationConfig.from_dict(config)
            app_config.validate()
            return True
        except Exception as e:
            raise ConfigurationError(f"Configuration validation failed: {e}")
    
    def set_validator(self, validator: ConfigurationValidatorInterface) -> None:
        """Set configuration validator.
        
        Args:
            validator: Configuration validator to use.
        """
        self._validator = validator
    
    def reload_config(self) -> Dict[str, Any]:
        """Reload configuration from all sources.
        
        Returns:
            Reloaded configuration dictionary.
        """
        # Clear cache to force reload
        self._cached_config = None
        return self.load_config()
    
    def get_config_sources(self) -> List[str]:
        """Get list of configuration sources in priority order.
        
        Returns:
            List of configuration source names.
        """
        return self._config_sources.copy()
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get information about configuration sources and status.
        
        Returns:
            Dictionary containing configuration metadata.
        """
        info = {
            "config_dir": str(self._config_dir),
            "sources": self._config_sources,
            "cached": self._cached_config is not None,
            "validator_set": self._validator is not None
        }
        
        # Add information about each handler
        handlers_info = {}
        for handler in self._get_all_handlers():
            handler_name = handler.__class__.__name__
            try:
                handler_config = handler.load_all()
                handlers_info[handler_name] = {
                    "available": True,
                    "settings_count": len(handler_config) if handler_config else 0
                }
            except Exception as e:
                handlers_info[handler_name] = {
                    "available": False,
                    "error": str(e)
                }
        
        info["handlers"] = handlers_info
        return info
    
    def export_config(self, output_path: Path, format_type: str = "json") -> None:
        """Export current configuration to file.
        
        Args:
            output_path: Path where to save the configuration.
            format_type: Format for export ('json' or 'yaml').
            
        Raises:
            ConfigurationError: If export fails.
        """
        try:
            config = self.load_config()
            
            if format_type.lower() == "json":
                import json
                with open(output_path, 'w') as f:
                    json.dump(config, f, indent=2, default=str)
            elif format_type.lower() == "yaml":
                try:
                    import yaml
                    with open(output_path, 'w') as f:
                        yaml.dump(config, f, default_flow_style=False)
                except ImportError:
                    raise ConfigurationError("PyYAML not available for YAML export")
            else:
                raise ConfigurationError(f"Unsupported export format: {format_type}")
            
            logger.info(f"Configuration exported to {output_path}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to export configuration: {e}")