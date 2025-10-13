"""CLI utility functions and helpers.

This module provides utility functions for CLI operations including
color-coded output, input validation, user confirmation prompts,
and error handling with message formatting.
"""

from __future__ import annotations
import re
import sys
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from pathlib import Path

import click
try:
    from colorama import init as colorama_init, Fore, Style, Back
    colorama_init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    # Fallback color definitions
    class Fore:
        RED = GREEN = BLUE = YELLOW = CYAN = MAGENTA = WHITE = RESET = ""
    
    class Style:
        BRIGHT = DIM = RESET_ALL = ""
    
    class Back:
        RED = GREEN = BLUE = YELLOW = CYAN = MAGENTA = WHITE = RESET = ""


# Color-coded output helpers
def success_message(message: str, bold: bool = False) -> None:
    """Display success message in green."""
    if COLORAMA_AVAILABLE:
        style = Style.BRIGHT if bold else ""
        click.echo(f"{style}{Fore.GREEN}✓ {message}{Style.RESET_ALL}")
    else:
        click.echo(click.style(f"✓ {message}", fg='green', bold=bold))


def error_message(message: str, bold: bool = True) -> None:
    """Display error message in red."""
    if COLORAMA_AVAILABLE:
        style = Style.BRIGHT if bold else ""
        click.echo(f"{style}{Fore.RED}✗ {message}{Style.RESET_ALL}", err=True)
    else:
        click.echo(click.style(f"✗ {message}", fg='red', bold=bold), err=True)


def info_message(message: str, bold: bool = False) -> None:
    """Display info message in blue."""
    if COLORAMA_AVAILABLE:
        style = Style.BRIGHT if bold else ""
        click.echo(f"{style}{Fore.BLUE}ℹ {message}{Style.RESET_ALL}")
    else:
        click.echo(click.style(f"ℹ {message}", fg='blue', bold=bold))


def warning_message(message: str, bold: bool = False) -> None:
    """Display warning message in yellow."""
    if COLORAMA_AVAILABLE:
        style = Style.BRIGHT if bold else ""
        click.echo(f"{style}{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}", err=True)
    else:
        click.echo(click.style(f"⚠ {message}", fg='yellow', bold=bold), err=True)


def debug_message(message: str) -> None:
    """Display debug message in dim style."""
    if COLORAMA_AVAILABLE:
        click.echo(f"{Style.DIM}{Fore.CYAN}🔍 {message}{Style.RESET_ALL}", err=True)
    else:
        click.echo(click.style(f"🔍 {message}", fg='cyan', dim=True), err=True)


def highlight_text(text: str, color: str = 'cyan', bold: bool = True) -> str:
    """Highlight text with specified color."""
    if COLORAMA_AVAILABLE:
        color_map = {
            'red': Fore.RED,
            'green': Fore.GREEN,
            'blue': Fore.BLUE,
            'yellow': Fore.YELLOW,
            'cyan': Fore.CYAN,
            'magenta': Fore.MAGENTA,
            'white': Fore.WHITE
        }
        style = Style.BRIGHT if bold else ""
        color_code = color_map.get(color.lower(), Fore.CYAN)
        return f"{style}{color_code}{text}{Style.RESET_ALL}"
    else:
        return click.style(text, fg=color, bold=bold)


# Input validation functions
def validate_ticket_id_format(ticket_id: str) -> bool:
    """Validate ticket ID format against known patterns."""
    patterns = [
        r'^[A-Z]{1,5}-?\d{1,10}$',  # Standard format: ABC-123456
        r'^T\d{6,10}$',             # T-format: T123456
        r'^P\d{6,10}$',             # P-format: P123456
        r'^V\d{10}$',               # V-format: V1234567890
    ]
    
    return any(re.match(pattern, ticket_id, re.IGNORECASE) for pattern in patterns)


def validate_email_format(email: str) -> bool:
    """Validate email address format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_date_format(date_str: str, format_str: str = "%Y-%m-%d") -> bool:
    """Validate date string format."""
    try:
        datetime.strptime(date_str, format_str)
        return True
    except ValueError:
        return False


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters."""
    # Remove invalid characters for filenames
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    
    # Limit length
    if len(sanitized) > 255:
        name, ext = Path(sanitized).stem, Path(sanitized).suffix
        max_name_len = 255 - len(ext)
        sanitized = name[:max_name_len] + ext
    
    return sanitized or "unnamed_file"


# User confirmation prompts
def confirm_action(message: str, default: bool = False, 
                  abort_on_no: bool = False) -> bool:
    """Prompt user for confirmation with colored output."""
    prompt_text = f"{Fore.YELLOW}❓ {message}{Style.RESET_ALL}" if COLORAMA_AVAILABLE else message
    
    try:
        result = click.confirm(prompt_text, default=default, abort=abort_on_no)
        return result
    except click.Abort:
        if abort_on_no:
            error_message("Operation aborted by user")
            sys.exit(1)
        return False


def prompt_for_input(message: str, default: Optional[str] = None,
                    validation_func: Optional[callable] = None,
                    max_attempts: int = 3) -> str:
    """Prompt user for input with validation."""
    prompt_text = f"{Fore.CYAN}❓ {message}{Style.RESET_ALL}" if COLORAMA_AVAILABLE else message
    
    for attempt in range(max_attempts):
        try:
            value = click.prompt(prompt_text, default=default, type=str)
            
            if validation_func and not validation_func(value):
                error_message(f"Invalid input. Please try again. ({attempt + 1}/{max_attempts})")
                continue
            
            return value
        except click.Abort:
            error_message("Input cancelled by user")
            sys.exit(1)
    
    error_message(f"Maximum attempts ({max_attempts}) exceeded")
    sys.exit(1)


def select_from_options(message: str, options: List[str], 
                       default: Optional[int] = None) -> str:
    """Present user with a list of options to select from."""
    if not options:
        error_message("No options available")
        return ""
    
    # Display options
    info_message(message)
    for i, option in enumerate(options, 1):
        marker = " (default)" if default == i else ""
        click.echo(f"  {i}. {option}{marker}")
    
    # Get user selection
    while True:
        try:
            prompt_text = "Select option"
            if default:
                prompt_text += f" (default: {default})"
            
            choice = click.prompt(prompt_text, type=int, default=default)
            
            if 1 <= choice <= len(options):
                return options[choice - 1]
            else:
                error_message(f"Please select a number between 1 and {len(options)}")
        except click.Abort:
            error_message("Selection cancelled by user")
            sys.exit(1)


# Table formatting functions
def format_table_output(data: Any, headers: Optional[List[str]] = None) -> str:
    """Format data as a table for CLI display."""
    if not data:
        return "No data to display"
    
    try:
        # Try to use tabulate if available
        from tabulate import tabulate
        
        if hasattr(data, 'to_dict'):
            # Handle analysis results
            table_data = _convert_analysis_to_table(data)
        elif isinstance(data, list) and data:
            if isinstance(data[0], dict):
                # List of dictionaries
                if not headers:
                    headers = list(data[0].keys())
                table_data = [[row.get(h, '') for h in headers] for row in data]
            else:
                # Simple list
                table_data = [[item] for item in data]
                headers = headers or ["Value"]
        elif isinstance(data, dict):
            # Dictionary data
            table_data = [[k, v] for k, v in data.items()]
            headers = headers or ["Key", "Value"]
        else:
            # Fallback
            table_data = [[str(data)]]
            headers = headers or ["Data"]
        
        return tabulate(table_data, headers=headers, tablefmt="grid")
    
    except ImportError:
        # Fallback to simple formatting
        return _format_simple_table(data, headers)


def _convert_analysis_to_table(analysis_result: Any) -> List[List[str]]:
    """Convert analysis result to table format."""
    table_data = []
    
    # Basic info
    table_data.append(["Total Tickets", str(analysis_result.ticket_count)])
    table_data.append(["Analysis Date", str(analysis_result.generated_at)])
    
    # Metrics
    if hasattr(analysis_result, 'metrics') and analysis_result.metrics:
        for key, value in analysis_result.metrics.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    table_data.append([f"{key}.{sub_key}", str(sub_value)])
            else:
                table_data.append([key, str(value)])
    
    return table_data


def _format_simple_table(data: Any, headers: Optional[List[str]]) -> str:
    """Simple table formatting fallback."""
    lines = []
    
    if isinstance(data, dict):
        max_key_len = max(len(str(k)) for k in data.keys()) if data else 0
        for key, value in data.items():
            lines.append(f"{str(key):<{max_key_len}} | {value}")
    elif isinstance(data, list) and data:
        if isinstance(data[0], dict):
            # List of dictionaries
            if not headers:
                headers = list(data[0].keys())
            
            # Calculate column widths
            col_widths = [len(h) for h in headers]
            for row in data:
                for i, header in enumerate(headers):
                    col_widths[i] = max(col_widths[i], len(str(row.get(header, ''))))
            
            # Format header
            header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
            lines.append(header_line)
            lines.append("-" * len(header_line))
            
            # Format rows
            for row in data:
                row_line = " | ".join(
                    str(row.get(h, '')).ljust(col_widths[i]) 
                    for i, h in enumerate(headers)
                )
                lines.append(row_line)
        else:
            # Simple list
            for item in data:
                lines.append(str(item))
    else:
        lines.append(str(data))
    
    return "\n".join(lines)


def list_files_with_details(file_paths: List[Path]) -> str:
    """List files with detailed information."""
    if not file_paths:
        return "No files found"
    
    table_data = []
    for file_path in file_paths:
        try:
            stat = file_path.stat()
            size = _format_file_size(stat.st_size)
            modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
            table_data.append([file_path.name, size, modified])
        except Exception as e:
            table_data.append([file_path.name, "Error", str(e)])
    
    headers = ["Filename", "Size", "Modified"]
    return format_table_output(table_data, headers)


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


# Configuration display formatting
def format_config_display(config_data: Dict[str, Any], 
                         show_sources: bool = False) -> str:
    """Format configuration data for display."""
    lines = []
    
    def _format_section(data: Dict[str, Any], prefix: str = "") -> None:
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                if show_sources and "_source" in value:
                    # Handle source information
                    actual_value = {k: v for k, v in value.items() if k != "_source"}
                    source = value["_source"]
                    if actual_value:
                        _format_section(actual_value, full_key)
                    else:
                        lines.append(f"{full_key}: {source}")
                else:
                    _format_section(value, full_key)
            else:
                if show_sources:
                    lines.append(f"{full_key}: {value}")
                else:
                    lines.append(f"{full_key}: {value}")
    
    _format_section(config_data)
    return "\n".join(lines)


# Error message formatting
def format_exception_message(exception: Exception, 
                           include_traceback: bool = False) -> str:
    """Format exception message for CLI display."""
    message = str(exception)
    
    if include_traceback:
        import traceback
        tb = traceback.format_exc()
        message += f"\n\nTraceback:\n{tb}"
    
    return message


def format_validation_errors(errors: List[str]) -> str:
    """Format validation errors for display."""
    if not errors:
        return "No validation errors"
    
    lines = ["Validation errors:"]
    for i, error in enumerate(errors, 1):
        lines.append(f"  {i}. {error}")
    
    return "\n".join(lines)


# Progress and status indicators
def show_spinner(message: str = "Processing...") -> 'SpinnerContext':
    """Show a spinner for long-running operations."""
    return SpinnerContext(message)


class SpinnerContext:
    """Context manager for showing spinner during operations."""
    
    def __init__(self, message: str) -> None:
        self.message = message
        self.spinner_chars = "|/-\\"
        self.spinner_index = 0
        self.running = False
        self.thread = None
    
    def __enter__(self) -> 'SpinnerContext':
        self.start()
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()
    
    def start(self) -> None:
        """Start the spinner."""
        import threading
        import time
        
        self.running = True
        
        def spin():
            while self.running:
                char = self.spinner_chars[self.spinner_index]
                click.echo(f"\r{char} {self.message}", nl=False, err=True)
                self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
                time.sleep(0.1)
        
        self.thread = threading.Thread(target=spin, daemon=True)
        self.thread.start()
    
    def stop(self) -> None:
        """Stop the spinner."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=0.5)
        click.echo("\r" + " " * (len(self.message) + 2) + "\r", nl=False, err=True)


# Utility functions for CLI operations
def get_terminal_width() -> int:
    """Get terminal width for formatting."""
    try:
        return click.get_terminal_size()[0]
    except:
        return 80  # Default width


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to specified length."""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def wrap_text(text: str, width: Optional[int] = None) -> str:
    """Wrap text to specified width."""
    if width is None:
        width = get_terminal_width() - 4  # Leave some margin
    
    import textwrap
    return textwrap.fill(text, width=width)


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def create_progress_callback(description: str = "Processing") -> callable:
    """Create a progress callback function for use with services."""
    try:
        from tqdm import tqdm
        pbar = tqdm(desc=description, unit="items")
        
        def callback(current: int, total: Optional[int] = None) -> None:
            if total and pbar.total != total:
                pbar.total = total
            pbar.update(1)
        
        return callback
    except ImportError:
        # Fallback without tqdm
        def callback(current: int, total: Optional[int] = None) -> None:
            if total:
                percent = (current / total) * 100
                click.echo(f"\r{description}: {current}/{total} ({percent:.1f}%)", nl=False, err=True)
            else:
                click.echo(f"\r{description}: {current}", nl=False, err=True)
        
        return callback