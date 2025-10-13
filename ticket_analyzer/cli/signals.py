"""Signal handling and graceful shutdown for CLI operations.

This module provides signal handling capabilities for graceful shutdown,
progress interruption, and proper resource cleanup during CLI operations.
"""

from __future__ import annotations
import signal
import sys
import threading
import time
from typing import Optional, Callable, Any, List, Dict
from pathlib import Path
import logging

import click

logger = logging.getLogger(__name__)


class GracefulShutdown:
    """Handle graceful shutdown with proper resource cleanup."""
    
    def __init__(self) -> None:
        self.shutdown_requested = False
        self.cleanup_functions: List[Callable[[], None]] = []
        self.temp_files: List[Path] = []
        self.active_processes: List[Any] = []
        self.progress_bars: List[Any] = []
        self._original_handlers: Dict[int, Any] = {}
        self._lock = threading.Lock()
        
        # Register signal handlers
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        # Handle SIGINT (Ctrl+C)
        self._original_handlers[signal.SIGINT] = signal.signal(
            signal.SIGINT, self._handle_interrupt
        )
        
        # Handle SIGTERM (termination request)
        if hasattr(signal, 'SIGTERM'):
            self._original_handlers[signal.SIGTERM] = signal.signal(
                signal.SIGTERM, self._handle_termination
            )
        
        # Handle SIGPIPE (broken pipe) on Unix systems
        if hasattr(signal, 'SIGPIPE'):
            self._original_handlers[signal.SIGPIPE] = signal.signal(
                signal.SIGPIPE, signal.SIG_DFL
            )
    
    def _handle_interrupt(self, signum: int, frame: Any) -> None:
        """Handle SIGINT (Ctrl+C) signal."""
        with self._lock:
            if self.shutdown_requested:
                # Second interrupt - force exit
                click.echo(
                    click.style("\nForced shutdown...", fg='red', bold=True),
                    err=True
                )
                self._force_exit()
            else:
                # First interrupt - graceful shutdown
                self.shutdown_requested = True
                click.echo(
                    click.style("\nShutdown requested... (Press Ctrl+C again to force)", 
                              fg='yellow'),
                    err=True
                )
                self._initiate_graceful_shutdown()
    
    def _handle_termination(self, signum: int, frame: Any) -> None:
        """Handle SIGTERM signal."""
        with self._lock:
            self.shutdown_requested = True
            click.echo(
                click.style("\nTermination requested...", fg='yellow'),
                err=True
            )
            self._initiate_graceful_shutdown()
    
    def _initiate_graceful_shutdown(self) -> None:
        """Initiate graceful shutdown process."""
        try:
            # Stop progress bars
            self._stop_progress_bars()
            
            # Terminate active processes
            self._terminate_processes()
            
            # Run cleanup functions
            self._run_cleanup_functions()
            
            # Clean up temporary files
            self._cleanup_temp_files()
            
            click.echo(
                click.style("Cleanup completed.", fg='green'),
                err=True
            )
            
        except Exception as e:
            logger.error(f"Error during graceful shutdown: {e}")
            click.echo(
                click.style(f"Cleanup error: {e}", fg='red'),
                err=True
            )
        finally:
            sys.exit(130)  # Standard exit code for SIGINT
    
    def _force_exit(self) -> None:
        """Force immediate exit without cleanup."""
        # Restore original signal handlers
        for signum, handler in self._original_handlers.items():
            signal.signal(signum, handler)
        
        sys.exit(1)
    
    def _stop_progress_bars(self) -> None:
        """Stop all active progress bars."""
        for pbar in self.progress_bars:
            try:
                if hasattr(pbar, 'close'):
                    pbar.close()
                elif hasattr(pbar, 'finish'):
                    pbar.finish()
            except Exception as e:
                logger.debug(f"Error stopping progress bar: {e}")
    
    def _terminate_processes(self) -> None:
        """Terminate all active processes."""
        for process in self.active_processes:
            try:
                if hasattr(process, 'terminate'):
                    process.terminate()
                    # Give process time to terminate gracefully
                    if hasattr(process, 'wait'):
                        try:
                            process.wait(timeout=5)
                        except:
                            # Force kill if doesn't terminate
                            if hasattr(process, 'kill'):
                                process.kill()
            except Exception as e:
                logger.debug(f"Error terminating process: {e}")
    
    def _run_cleanup_functions(self) -> None:
        """Run all registered cleanup functions."""
        for cleanup_func in self.cleanup_functions:
            try:
                cleanup_func()
            except Exception as e:
                logger.error(f"Error in cleanup function: {e}")
    
    def _cleanup_temp_files(self) -> None:
        """Clean up temporary files."""
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                logger.error(f"Error cleaning up temp file {temp_file}: {e}")
    
    def register_cleanup_function(self, func: Callable[[], None]) -> None:
        """Register a cleanup function to be called on shutdown."""
        with self._lock:
            self.cleanup_functions.append(func)
    
    def register_temp_file(self, file_path: Path) -> None:
        """Register a temporary file for cleanup."""
        with self._lock:
            self.temp_files.append(file_path)
    
    def register_process(self, process: Any) -> None:
        """Register a process for termination on shutdown."""
        with self._lock:
            self.active_processes.append(process)
    
    def register_progress_bar(self, pbar: Any) -> None:
        """Register a progress bar for cleanup."""
        with self._lock:
            self.progress_bars.append(pbar)
    
    def unregister_process(self, process: Any) -> None:
        """Unregister a process (when it completes normally)."""
        with self._lock:
            if process in self.active_processes:
                self.active_processes.remove(process)
    
    def unregister_progress_bar(self, pbar: Any) -> None:
        """Unregister a progress bar (when it completes normally)."""
        with self._lock:
            if pbar in self.progress_bars:
                self.progress_bars.remove(pbar)
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested."""
        return self.shutdown_requested
    
    def restore_signal_handlers(self) -> None:
        """Restore original signal handlers."""
        for signum, handler in self._original_handlers.items():
            signal.signal(signum, handler)


class InterruptibleOperation:
    """Context manager for operations that can be interrupted gracefully."""
    
    def __init__(self, shutdown_handler: GracefulShutdown, 
                 operation_name: str = "operation") -> None:
        self.shutdown_handler = shutdown_handler
        self.operation_name = operation_name
        self.cleanup_functions: List[Callable[[], None]] = []
    
    def __enter__(self) -> 'InterruptibleOperation':
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        # Run operation-specific cleanup
        for cleanup_func in self.cleanup_functions:
            try:
                cleanup_func()
            except Exception as e:
                logger.error(f"Error in operation cleanup: {e}")
    
    def add_cleanup(self, func: Callable[[], None]) -> None:
        """Add cleanup function for this operation."""
        self.cleanup_functions.append(func)
    
    def check_interruption(self) -> None:
        """Check if interruption was requested and raise exception if so."""
        if self.shutdown_handler.is_shutdown_requested():
            raise KeyboardInterrupt(f"Operation '{self.operation_name}' interrupted")


class ProgressTracker:
    """Progress tracker with interruption support."""
    
    def __init__(self, shutdown_handler: GracefulShutdown, 
                 total: Optional[int] = None, desc: str = "Processing") -> None:
        self.shutdown_handler = shutdown_handler
        self.total = total
        self.desc = desc
        self.current = 0
        self.pbar: Optional[Any] = None
    
    def __enter__(self) -> 'ProgressTracker':
        try:
            from tqdm import tqdm
            self.pbar = tqdm(total=self.total, desc=self.desc, unit="item")
            self.shutdown_handler.register_progress_bar(self.pbar)
        except ImportError:
            # Fallback if tqdm not available
            self.pbar = None
        
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.pbar:
            self.shutdown_handler.unregister_progress_bar(self.pbar)
            self.pbar.close()
    
    def update(self, n: int = 1) -> None:
        """Update progress and check for interruption."""
        self.current += n
        
        if self.pbar:
            self.pbar.update(n)
        else:
            # Simple text progress if tqdm not available
            if self.total:
                percent = (self.current / self.total) * 100
                click.echo(f"\r{self.desc}: {self.current}/{self.total} ({percent:.1f}%)", nl=False, err=True)
            else:
                click.echo(f"\r{self.desc}: {self.current}", nl=False, err=True)
        
        # Check for interruption
        if self.shutdown_handler.is_shutdown_requested():
            raise KeyboardInterrupt("Progress tracking interrupted")
    
    def set_description(self, desc: str) -> None:
        """Update progress description."""
        self.desc = desc
        if self.pbar:
            self.pbar.set_description(desc)


def with_graceful_shutdown(func: Callable) -> Callable:
    """Decorator to add graceful shutdown handling to CLI commands."""
    def wrapper(*args, **kwargs):
        shutdown_handler = GracefulShutdown()
        
        # Add shutdown handler to context if available
        ctx = click.get_current_context(silent=True)
        if ctx and hasattr(ctx, 'obj') and ctx.obj:
            ctx.obj.shutdown_handler = shutdown_handler
        
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            click.echo(
                click.style("\nOperation cancelled by user", fg='yellow'),
                err=True
            )
            sys.exit(130)
        finally:
            shutdown_handler.restore_signal_handlers()
    
    return wrapper


def create_temp_file_manager(shutdown_handler: GracefulShutdown) -> 'TempFileManager':
    """Create a temporary file manager with automatic cleanup."""
    return TempFileManager(shutdown_handler)


class TempFileManager:
    """Manage temporary files with automatic cleanup on shutdown."""
    
    def __init__(self, shutdown_handler: GracefulShutdown) -> None:
        self.shutdown_handler = shutdown_handler
        self.temp_files: List[Path] = []
    
    def create_temp_file(self, suffix: str = ".tmp", 
                        prefix: str = "ticket_analyzer_") -> Path:
        """Create a temporary file."""
        import tempfile
        
        fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
        import os
        os.close(fd)  # Close file descriptor, keep path
        
        temp_file = Path(temp_path)
        self.temp_files.append(temp_file)
        self.shutdown_handler.register_temp_file(temp_file)
        
        return temp_file
    
    def cleanup_file(self, file_path: Path) -> None:
        """Clean up a specific temporary file."""
        try:
            if file_path.exists():
                file_path.unlink()
            
            if file_path in self.temp_files:
                self.temp_files.remove(file_path)
        except Exception as e:
            logger.error(f"Error cleaning up temp file {file_path}: {e}")
    
    def cleanup_all(self) -> None:
        """Clean up all temporary files."""
        for temp_file in self.temp_files.copy():
            self.cleanup_file(temp_file)


# Exit codes for different scenarios
class ExitCodes:
    """Standard exit codes for the application."""
    
    SUCCESS = 0
    GENERAL_ERROR = 1
    CONFIGURATION_ERROR = 2
    DATA_ERROR = 3
    ANALYSIS_ERROR = 4
    AUTHENTICATION_ERROR = 5
    INTERRUPTED = 130  # Standard code for SIGINT
    TERMINATED = 143   # Standard code for SIGTERM


def handle_exit_code(exception: Exception) -> int:
    """Determine appropriate exit code for exception."""
    from ..models.exceptions import (
        ConfigurationError,
        AuthenticationError,
        DataRetrievalError,
        AnalysisError
    )
    
    if isinstance(exception, KeyboardInterrupt):
        return ExitCodes.INTERRUPTED
    elif isinstance(exception, AuthenticationError):
        return ExitCodes.AUTHENTICATION_ERROR
    elif isinstance(exception, ConfigurationError):
        return ExitCodes.CONFIGURATION_ERROR
    elif isinstance(exception, DataRetrievalError):
        return ExitCodes.DATA_ERROR
    elif isinstance(exception, AnalysisError):
        return ExitCodes.ANALYSIS_ERROR
    else:
        return ExitCodes.GENERAL_ERROR