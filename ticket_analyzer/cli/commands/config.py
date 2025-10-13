"""Configuration command implementation.

This module implements configuration management commands for viewing,
updating, and validating application settings.
"""

from __future__ import annotations
import sys
from typing import Optional, Dict, Any
from pathlib import Path

import click

from ...models.exceptions import ConfigurationError
from ..utils import (
    success_message,
    error_message,
    info_message,
    warning_message,
    format_config_display
)
from ..main import handle_cli_errors


@click.group("config")
@click.pass_context
def config_command(ctx: click.Context) -> None:
    """Configuration management commands.
    
    View, update, and validate application configuration settings.
    Supports both JSON and INI configuration file formats.
    """
    pass


@config_command.command("show")
@click.option(
    "--config-file",
    type=click.Path(exists=True, path_type=Path),
    help="Specific configuration file to display"
)
@click.option(
    "--section",
    help="Show only specific configuration section"
)
@click.option(
    "--format",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format for configuration display"
)
@click.option(
    "--show-defaults",
    is_flag=True,
    help="Include default values in output"
)
@click.option(
    "--show-sources",
    is_flag=True,
    help="Show configuration value sources (file, env, default)"
)
@click.pass_context
@handle_cli_errors
def show_config(
    ctx: click.Context,
    config_file: Optional[Path],
    section: Optional[str],
    format: str,
    show_defaults: bool,
    show_sources: bool
) -> None:
    """Display current configuration settings.
    
    Shows the effective configuration including values from files,
    environment variables, and defaults.
    
    Examples:
        ticket-analyzer config show
        ticket-analyzer config show --section authentication
        ticket-analyzer config show --format json --show-sources
    """
    try:
        from ...container import DependencyContainer
        container = DependencyContainer()
        
        config_manager = container.config_manager
        
        # Load configuration
        if config_file:
            config_data = config_manager.load_from_file(config_file)
        else:
            config_data = config_manager.get_effective_config()
        
        # Filter by section if specified
        if section:
            if section in config_data:
                config_data = {section: config_data[section]}
            else:
                warning_message(f"Section '{section}' not found in configuration")
                return
        
        # Add defaults if requested
        if show_defaults:
            defaults = config_manager.get_default_config()
            config_data = config_manager.merge_with_defaults(config_data, defaults)
        
        # Add source information if requested
        if show_sources:
            config_data = config_manager.add_source_info(config_data)
        
        # Display configuration
        if format == "table":
            formatted_output = format_config_display(config_data, show_sources)
            click.echo(formatted_output)
        elif format == "json":
            import json
            click.echo(json.dumps(config_data, indent=2, default=str))
        elif format == "yaml":
            import yaml
            click.echo(yaml.dump(config_data, default_flow_style=False))
        
        if ctx.obj.verbose:
            config_file_path = config_file or config_manager.get_config_file_path()
            info_message(f"Configuration loaded from: {config_file_path}")
    
    except ConfigurationError as e:
        error_message(f"Configuration error: {e}")
        sys.exit(2)
    except Exception as e:
        error_message(f"Failed to display configuration: {e}")
        sys.exit(1)


@config_command.command("set")
@click.argument("key")
@click.argument("value")
@click.option(
    "--config-file",
    type=click.Path(path_type=Path),
    help="Configuration file to update (creates if doesn't exist)"
)
@click.option(
    "--section",
    help="Configuration section for the key"
)
@click.option(
    "--type",
    type=click.Choice(["string", "int", "float", "bool", "list"]),
    default="string",
    help="Value type for proper conversion"
)
@click.option(
    "--create-backup",
    is_flag=True,
    default=True,
    help="Create backup before modifying configuration"
)
@click.pass_context
@handle_cli_errors
def set_config(
    ctx: click.Context,
    key: str,
    value: str,
    config_file: Optional[Path],
    section: Optional[str],
    type: str,
    create_backup: bool
) -> None:
    """Set a configuration value.
    
    Updates configuration files with new values, creating sections
    and files as needed.
    
    Examples:
        ticket-analyzer config set output_format json
        ticket-analyzer config set authentication.timeout 120 --type int
        ticket-analyzer config set tags "tag1,tag2,tag3" --type list
    """
    try:
        from ...container import DependencyContainer
        container = DependencyContainer()
        
        config_manager = container.config_manager
        
        # Convert value to appropriate type
        converted_value = _convert_config_value(value, type)
        
        # Determine config file path
        target_file = config_file or config_manager.get_default_config_file()
        
        # Create backup if requested
        if create_backup and target_file.exists():
            backup_path = target_file.with_suffix(f"{target_file.suffix}.backup")
            import shutil
            shutil.copy2(target_file, backup_path)
            if ctx.obj.verbose:
                info_message(f"Backup created: {backup_path}")
        
        # Update configuration
        config_manager.set_config_value(
            key=key,
            value=converted_value,
            section=section,
            config_file=target_file
        )
        
        success_message(f"Configuration updated: {key} = {converted_value}")
        
        if ctx.obj.verbose:
            info_message(f"Updated file: {target_file}")
    
    except ConfigurationError as e:
        error_message(f"Configuration error: {e}")
        sys.exit(2)
    except Exception as e:
        error_message(f"Failed to set configuration: {e}")
        sys.exit(1)


@config_command.command("unset")
@click.argument("key")
@click.option(
    "--config-file",
    type=click.Path(exists=True, path_type=Path),
    help="Configuration file to modify"
)
@click.option(
    "--section",
    help="Configuration section containing the key"
)
@click.option(
    "--create-backup",
    is_flag=True,
    default=True,
    help="Create backup before modifying configuration"
)
@click.pass_context
@handle_cli_errors
def unset_config(
    ctx: click.Context,
    key: str,
    config_file: Optional[Path],
    section: Optional[str],
    create_backup: bool
) -> None:
    """Remove a configuration value.
    
    Removes specified configuration keys from configuration files.
    
    Examples:
        ticket-analyzer config unset custom_setting
        ticket-analyzer config unset authentication.custom_timeout
    """
    try:
        from ...container import DependencyContainer
        container = DependencyContainer()
        
        config_manager = container.config_manager
        
        # Determine config file path
        target_file = config_file or config_manager.get_default_config_file()
        
        if not target_file.exists():
            error_message(f"Configuration file not found: {target_file}")
            sys.exit(2)
        
        # Create backup if requested
        if create_backup:
            backup_path = target_file.with_suffix(f"{target_file.suffix}.backup")
            import shutil
            shutil.copy2(target_file, backup_path)
            if ctx.obj.verbose:
                info_message(f"Backup created: {backup_path}")
        
        # Remove configuration value
        config_manager.unset_config_value(
            key=key,
            section=section,
            config_file=target_file
        )
        
        success_message(f"Configuration removed: {key}")
        
        if ctx.obj.verbose:
            info_message(f"Updated file: {target_file}")
    
    except ConfigurationError as e:
        error_message(f"Configuration error: {e}")
        sys.exit(2)
    except Exception as e:
        error_message(f"Failed to unset configuration: {e}")
        sys.exit(1)


@config_command.command("validate")
@click.option(
    "--config-file",
    type=click.Path(exists=True, path_type=Path),
    help="Configuration file to validate"
)
@click.option(
    "--strict",
    is_flag=True,
    help="Enable strict validation mode"
)
@click.option(
    "--fix-issues",
    is_flag=True,
    help="Attempt to fix validation issues automatically"
)
@click.pass_context
@handle_cli_errors
def validate_config(
    ctx: click.Context,
    config_file: Optional[Path],
    strict: bool,
    fix_issues: bool
) -> None:
    """Validate configuration file format and values.
    
    Checks configuration files for syntax errors, invalid values,
    and missing required settings.
    
    Examples:
        ticket-analyzer config validate
        ticket-analyzer config validate --strict --fix-issues
    """
    try:
        from ...container import DependencyContainer
        container = DependencyContainer()
        
        config_manager = container.config_manager
        
        # Determine config file to validate
        target_file = config_file or config_manager.get_default_config_file()
        
        if not target_file.exists():
            warning_message(f"Configuration file not found: {target_file}")
            info_message("Using default configuration values")
            return
        
        # Perform validation
        validation_result = config_manager.validate_config(
            config_file=target_file,
            strict_mode=strict
        )
        
        if validation_result.is_valid:
            success_message("Configuration validation passed")
        else:
            error_message("Configuration validation failed")
            
            # Display validation errors
            for error in validation_result.errors:
                error_message(f"  • {error}")
            
            # Display warnings
            for warning in validation_result.warnings:
                warning_message(f"  • {warning}")
            
            # Attempt fixes if requested
            if fix_issues and validation_result.fixable_issues:
                info_message("Attempting to fix issues...")
                
                fixed_config = config_manager.fix_config_issues(
                    config_file=target_file,
                    issues=validation_result.fixable_issues
                )
                
                if fixed_config:
                    success_message("Configuration issues fixed")
                    if ctx.obj.verbose:
                        info_message("Re-run validation to confirm fixes")
                else:
                    warning_message("Some issues could not be fixed automatically")
            
            sys.exit(2 if validation_result.errors else 0)
        
        if ctx.obj.verbose:
            info_message(f"Validated file: {target_file}")
            info_message(f"Configuration sections: {len(validation_result.sections)}")
    
    except ConfigurationError as e:
        error_message(f"Configuration error: {e}")
        sys.exit(2)
    except Exception as e:
        error_message(f"Validation failed: {e}")
        sys.exit(1)


@config_command.command("init")
@click.option(
    "--config-file",
    type=click.Path(path_type=Path),
    help="Configuration file to create"
)
@click.option(
    "--format",
    type=click.Choice(["json", "ini"]),
    default="json",
    help="Configuration file format"
)
@click.option(
    "--template",
    type=click.Choice(["minimal", "standard", "comprehensive"]),
    default="standard",
    help="Configuration template to use"
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite existing configuration file"
)
@click.pass_context
@handle_cli_errors
def init_config(
    ctx: click.Context,
    config_file: Optional[Path],
    format: str,
    template: str,
    overwrite: bool
) -> None:
    """Initialize a new configuration file.
    
    Creates a new configuration file with default values and
    comprehensive documentation.
    
    Examples:
        ticket-analyzer config init
        ticket-analyzer config init --format ini --template comprehensive
    """
    try:
        from ...container import DependencyContainer
        container = DependencyContainer()
        
        config_manager = container.config_manager
        
        # Determine config file path
        if config_file:
            target_file = config_file
        else:
            config_dir = Path.home() / ".ticket-analyzer"
            config_dir.mkdir(exist_ok=True)
            target_file = config_dir / f"config.{format}"
        
        # Check if file exists
        if target_file.exists() and not overwrite:
            error_message(f"Configuration file already exists: {target_file}")
            error_message("Use --overwrite to replace existing file")
            sys.exit(2)
        
        # Create configuration file
        config_manager.create_config_file(
            config_file=target_file,
            format=format,
            template=template
        )
        
        success_message(f"Configuration file created: {target_file}")
        
        if ctx.obj.verbose:
            info_message(f"Format: {format}")
            info_message(f"Template: {template}")
            info_message("Edit the file to customize settings for your environment")
    
    except ConfigurationError as e:
        error_message(f"Configuration error: {e}")
        sys.exit(2)
    except Exception as e:
        error_message(f"Failed to initialize configuration: {e}")
        sys.exit(1)


def _convert_config_value(value: str, value_type: str) -> Any:
    """Convert string value to appropriate type."""
    if value_type == "int":
        return int(value)
    elif value_type == "float":
        return float(value)
    elif value_type == "bool":
        return value.lower() in ("true", "yes", "1", "on")
    elif value_type == "list":
        return [item.strip() for item in value.split(",")]
    else:  # string
        return value


# Register commands with the config group from main.py
def register_config_commands(config_group):
    """Register config commands with the CLI group."""
    config_group.add_command(show_config)
    config_group.add_command(set_config)
    config_group.add_command(unset_config)
    config_group.add_command(validate_config)
    config_group.add_command(init_config)