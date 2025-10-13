"""Configuration management module with hierarchy support.

This module provides a comprehensive configuration management system that
supports multiple configuration sources with proper precedence handling.
The configuration hierarchy follows: CLI args > config files > env vars > defaults.
"""

from __future__ import annotations

from .config_manager import ConfigurationManager
from .handlers import (
    BaseConfigurationHandler,
    CommandLineConfigHandler,
    FileConfigHandler,
    EnvironmentConfigHandler,
    DefaultConfigHandler,
    ConfigurationValidator
)

__all__ = [
    "ConfigurationManager",
    "BaseConfigurationHandler",
    "CommandLineConfigHandler", 
    "FileConfigHandler",
    "EnvironmentConfigHandler",
    "DefaultConfigHandler",
    "ConfigurationValidator"
]