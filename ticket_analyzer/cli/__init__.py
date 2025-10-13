"""CLI package for ticket analyzer.

This package provides the command-line interface for the ticket analyzer
application, including commands, options, utilities, and signal handling.
"""

from .main import cli
from .utils import (
    success_message,
    error_message,
    info_message,
    warning_message,
    debug_message
)
from .signals import GracefulShutdown, with_graceful_shutdown
from .options import (
    TicketIDType,
    DateRangeType,
    ConfigFileType,
    OutputFormatType,
    validate_ticket_id_format
)

__all__ = [
    "cli",
    "success_message",
    "error_message", 
    "info_message",
    "warning_message",
    "debug_message",
    "GracefulShutdown",
    "with_graceful_shutdown",
    "TicketIDType",
    "DateRangeType",
    "ConfigFileType",
    "OutputFormatType",
    "validate_ticket_id_format"
]