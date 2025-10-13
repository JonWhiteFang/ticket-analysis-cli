"""Progress indicators and user feedback management.

This module provides comprehensive progress indication and user feedback capabilities
including progress bars, status messages, operation feedback, time estimates, and
graceful error display with color coding and context.
"""

from __future__ import annotations
import sys
import time
import threading
from typing import Optional, Dict, Any, List, Callable, Union
from datetime import datetime, timedelta
from contextlib import contextmanager
from enum import Enum

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    # Fallback progress bar implementation
    class tqdm:
        def __init__(self, *args, **kwargs):
            self.total = kwargs.get('total', 100)
            self.desc = kwargs.get('desc', 'Progress')
            self.current = 0
            self.start_time = time.time()
        
        def update(self, n=1):
            self.current += n
            self._display_progress()
        
        def set_description(self, desc):
            self.desc = desc
        
        def set_postfix(self, **kwargs):
            pass
        
        def close(self):
            pass
        
        def _display_progress(self):
            if self.total > 0:
                percent = (self.current / self.total) * 100
                print(f"\r{self.desc}: {percent:.1f}%", end='', flush=True)
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            self.close()

try:
    import colorama
    from colorama import Fore, Back, Style
    colorama.init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    # Fallback color constants
    class Fore:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""
    class Back:
        RED = GREEN = YELLOW = BLUE = MAGENTA = CYAN = WHITE = RESET = ""
    class Style:
        BRIGHT = DIM = NORMAL = RESET_ALL = ""

from ..interfaces import ProgressInterface
from ..models.exceptions import ReportGenerationError


class StatusType(Enum):
    """Types of status messages."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    DEBUG = "debug"


class SpinnerType(Enum):
    """Types of spinner animations."""
    DOTS = "dots"
    BARS = "bars"
    ARROWS = "arrows"
    CLOCK = "clock"


class ProgressManager(ProgressInterface):
    """Comprehensive progress management with indicators and user feedback.
    
    This class provides progress bars, status messages, spinners, and operation
    feedback with color coding, time estimates, and graceful error handling.
    Integrates with tqdm for advanced progress indication capabilities.
    """
    
    # Spinner animations
    SPINNER_ANIMATIONS = {
        SpinnerType.DOTS: ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
        SpinnerType.BARS: ["▁", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃"],
        SpinnerType.ARROWS: ["←", "↖", "↑", "↗", "→", "↘", "↓", "↙"],
        SpinnerType.CLOCK: ["🕐", "🕑", "🕒", "🕓", "🕔", "🕕", "🕖", "🕗", "🕘", "🕙", "🕚", "🕛"],
    }
    
    def __init__(self, 
                 use_colors: bool = True,
                 use_unicode: bool = True,
                 output_stream = None) -> None:
        """Initialize progress manager.
        
        Args:
            use_colors: Whether to use color output (default: True).
            use_unicode: Whether to use Unicode characters (default: True).
            output_stream: Output stream for messages (default: sys.stderr).
        """
        self._use_colors = use_colors and COLORAMA_AVAILABLE
        self._use_unicode = use_unicode
        self._output_stream = output_stream or sys.stderr
        
        # Progress tracking
        self._current_operation: Optional[str] = None
        self._operation_start_time: Optional[datetime] = None
        self._progress_bar: Optional[tqdm] = None
        
        # Spinner state
        self._spinner_active = False
        self._spinner_thread: Optional[threading.Thread] = None
        self._spinner_stop_event = threading.Event()
        
        # Color scheme
        self._init_colors()
    
    def _init_colors(self) -> None:
        """Initialize color scheme for different message types."""
        if self._use_colors:
            self._colors = {
                StatusType.INFO: Fore.BLUE + Style.BRIGHT,
                StatusType.SUCCESS: Fore.GREEN + Style.BRIGHT,
                StatusType.WARNING: Fore.YELLOW + Style.BRIGHT,
                StatusType.ERROR: Fore.RED + Style.BRIGHT,
                StatusType.DEBUG: Fore.MAGENTA,
            }
            self._reset = Style.RESET_ALL
        else:
            self._colors = {status_type: "" for status_type in StatusType}
            self._reset = ""
    
    def show_progress(self, current: int, total: int, description: str) -> None:
        """Show progress indicator for ongoing operation.
        
        Args:
            current: Current progress value.
            total: Total expected value.
            description: Description of the operation.
        """
        if not self._progress_bar or self._progress_bar.total != total:
            # Create new progress bar
            if self._progress_bar:
                self._progress_bar.close()
            
            self._progress_bar = tqdm(
                total=total,
                desc=description,
                unit="items",
                ncols=80,
                file=self._output_stream,
                colour='green' if self._use_colors else None
            )
        
        # Update progress
        if current > self._progress_bar.n:
            self._progress_bar.update(current - self._progress_bar.n)
        
        # Update description if changed
        if description != self._progress_bar.desc:
            self._progress_bar.set_description(description)
    
    def update_status(self, message: str, status_type: str = "info") -> None:
        """Update status message for user feedback.
        
        Args:
            message: Status message to display.
            status_type: Type of status (info, success, warning, error).
        """
        try:
            status_enum = StatusType(status_type.lower())
        except ValueError:
            status_enum = StatusType.INFO
        
        # Format message with color and timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = self._colors.get(status_enum, "")
        reset = self._reset
        
        # Add status icon
        icon = self._get_status_icon(status_enum)
        
        formatted_message = f"[{timestamp}] {color}{icon} {message}{reset}"
        
        # Print to output stream
        print(formatted_message, file=self._output_stream, flush=True)
    
    def start_operation(self, description: str) -> None:
        """Start a new operation with progress tracking.
        
        Args:
            description: Description of the operation being started.
        """
        self._current_operation = description
        self._operation_start_time = datetime.now()
        
        self.update_status(f"Starting: {description}", "info")
    
    def complete_operation(self, success: bool, message: str) -> None:
        """Complete current operation and show result.
        
        Args:
            success: Whether operation completed successfully.
            message: Completion message to display.
        """
        if self._progress_bar:
            self._progress_bar.close()
            self._progress_bar = None
        
        # Calculate duration
        duration_str = ""
        if self._operation_start_time:
            duration = datetime.now() - self._operation_start_time
            duration_str = f" (took {self._format_duration(duration)})"
        
        # Show completion message
        status_type = "success" if success else "error"
        full_message = f"{message}{duration_str}"
        self.update_status(full_message, status_type)
        
        # Reset operation state
        self._current_operation = None
        self._operation_start_time = None
    
    def show_spinner(self, message: str, spinner_type: SpinnerType = SpinnerType.DOTS) -> None:
        """Show spinner for indeterminate progress.
        
        Args:
            message: Message to display with spinner.
            spinner_type: Type of spinner animation to use.
        """
        if self._spinner_active:
            self.hide_spinner()
        
        self._spinner_active = True
        self._spinner_stop_event.clear()
        
        # Start spinner thread
        self._spinner_thread = threading.Thread(
            target=self._spinner_worker,
            args=(message, spinner_type),
            daemon=True
        )
        self._spinner_thread.start()
    
    def hide_spinner(self) -> None:
        """Hide currently displayed spinner."""
        if self._spinner_active:
            self._spinner_stop_event.set()
            if self._spinner_thread:
                self._spinner_thread.join(timeout=1.0)
            self._spinner_active = False
            
            # Clear spinner line
            print("\r" + " " * 80 + "\r", end="", file=self._output_stream, flush=True)
    
    @contextmanager
    def progress_context(self, 
                        description: str, 
                        total: Optional[int] = None,
                        show_spinner: bool = False):
        """Context manager for progress indication.
        
        Args:
            description: Operation description.
            total: Total items for progress bar (None for spinner).
            show_spinner: Whether to show spinner for indeterminate progress.
        
        Yields:
            Progress updater function or progress bar object.
        """
        self.start_operation(description)
        
        try:
            if total is not None:
                # Use progress bar
                with tqdm(
                    total=total,
                    desc=description,
                    unit="items",
                    file=self._output_stream,
                    colour='green' if self._use_colors else None
                ) as pbar:
                    yield pbar
            elif show_spinner:
                # Use spinner
                self.show_spinner(description)
                yield lambda: None  # Dummy updater
            else:
                # No progress indication
                yield lambda: None
            
            self.complete_operation(True, f"Completed: {description}")
            
        except Exception as e:
            self.complete_operation(False, f"Failed: {description} - {e}")
            raise
        finally:
            if show_spinner:
                self.hide_spinner()
    
    def show_error_with_context(self, 
                               error: Exception, 
                               context: Optional[Dict[str, Any]] = None,
                               suggestions: Optional[List[str]] = None) -> None:
        """Display error with context and suggestions.
        
        Args:
            error: Exception that occurred.
            context: Additional context information.
            suggestions: List of suggested solutions.
        """
        # Error header
        error_color = self._colors.get(StatusType.ERROR, "")
        reset = self._reset
        
        print(f"\n{error_color}{'='*60}{reset}", file=self._output_stream)
        print(f"{error_color}ERROR: {type(error).__name__}{reset}", file=self._output_stream)
        print(f"{error_color}{'='*60}{reset}", file=self._output_stream)
        
        # Error message
        print(f"\n{error_color}Message:{reset} {str(error)}", file=self._output_stream)
        
        # Context information
        if context:
            print(f"\n{self._colors.get(StatusType.INFO, '')}Context:{reset}", file=self._output_stream)
            for key, value in context.items():
                print(f"  {key}: {value}", file=self._output_stream)
        
        # Current operation
        if self._current_operation:
            print(f"\n{self._colors.get(StatusType.INFO, '')}Current Operation:{reset} {self._current_operation}", file=self._output_stream)
        
        # Suggestions
        if suggestions:
            print(f"\n{self._colors.get(StatusType.WARNING, '')}Suggestions:{reset}", file=self._output_stream)
            for i, suggestion in enumerate(suggestions, 1):
                print(f"  {i}. {suggestion}", file=self._output_stream)
        
        print(f"\n{error_color}{'='*60}{reset}\n", file=self._output_stream)
    
    def show_summary_statistics(self, 
                              stats: Dict[str, Any],
                              title: str = "Operation Summary") -> None:
        """Display summary statistics with formatting.
        
        Args:
            stats: Statistics dictionary to display.
            title: Title for the summary section.
        """
        header_color = self._colors.get(StatusType.INFO, "")
        value_color = self._colors.get(StatusType.SUCCESS, "")
        reset = self._reset
        
        print(f"\n{header_color}{title}{reset}", file=self._output_stream)
        print(f"{header_color}{'-' * len(title)}{reset}", file=self._output_stream)
        
        # Calculate max key length for alignment
        max_key_length = max(len(str(key)) for key in stats.keys()) if stats else 0
        
        for key, value in stats.items():
            key_formatted = f"{key}:".ljust(max_key_length + 1)
            print(f"  {key_formatted} {value_color}{value}{reset}", file=self._output_stream)
        
        print("", file=self._output_stream)  # Empty line
    
    def create_progress_callback(self, 
                               description: str,
                               total: Optional[int] = None) -> Callable[[int], None]:
        """Create a progress callback function for use with other operations.
        
        Args:
            description: Description for the progress operation.
            total: Total number of items (None for indeterminate).
            
        Returns:
            Callback function that accepts current progress value.
        """
        if total is not None:
            pbar = tqdm(
                total=total,
                desc=description,
                unit="items",
                file=self._output_stream,
                colour='green' if self._use_colors else None
            )
            
            def callback(current: int) -> None:
                if current > pbar.n:
                    pbar.update(current - pbar.n)
                if current >= total:
                    pbar.close()
            
            return callback
        else:
            # For indeterminate progress, just show periodic updates
            last_update = [0]  # Use list for mutable reference
            
            def callback(current: int) -> None:
                if current - last_update[0] >= 10:  # Update every 10 items
                    self.update_status(f"{description}: processed {current} items", "info")
                    last_update[0] = current
            
            return callback
    
    def _get_status_icon(self, status_type: StatusType) -> str:
        """Get icon for status type."""
        if not self._use_unicode:
            return {
                StatusType.INFO: "[INFO]",
                StatusType.SUCCESS: "[OK]",
                StatusType.WARNING: "[WARN]",
                StatusType.ERROR: "[ERROR]",
                StatusType.DEBUG: "[DEBUG]",
            }.get(status_type, "[INFO]")
        
        return {
            StatusType.INFO: "ℹ️",
            StatusType.SUCCESS: "✅",
            StatusType.WARNING: "⚠️",
            StatusType.ERROR: "❌",
            StatusType.DEBUG: "🔍",
        }.get(status_type, "ℹ️")
    
    def _format_duration(self, duration: timedelta) -> str:
        """Format duration in human-readable format."""
        total_seconds = int(duration.total_seconds())
        
        if total_seconds < 1:
            return "< 1s"
        elif total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    
    def _spinner_worker(self, message: str, spinner_type: SpinnerType) -> None:
        """Worker thread for spinner animation."""
        animation = self.SPINNER_ANIMATIONS.get(spinner_type, self.SPINNER_ANIMATIONS[SpinnerType.DOTS])
        frame_index = 0
        
        while not self._spinner_stop_event.is_set():
            # Display current frame
            frame = animation[frame_index % len(animation)]
            spinner_line = f"\r{frame} {message}"
            
            print(spinner_line, end="", file=self._output_stream, flush=True)
            
            # Wait for next frame or stop event
            if self._spinner_stop_event.wait(0.1):  # 100ms per frame
                break
            
            frame_index += 1
    
    def __del__(self) -> None:
        """Cleanup when object is destroyed."""
        if self._spinner_active:
            self.hide_spinner()
        if self._progress_bar:
            self._progress_bar.close()


class OperationTimer:
    """Timer for tracking operation durations and providing estimates."""
    
    def __init__(self) -> None:
        """Initialize operation timer."""
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._checkpoints: List[Tuple[str, datetime]] = []
    
    def start(self) -> None:
        """Start timing the operation."""
        self._start_time = datetime.now()
        self._end_time = None
        self._checkpoints.clear()
    
    def checkpoint(self, name: str) -> None:
        """Add a checkpoint with the given name.
        
        Args:
            name: Name of the checkpoint.
        """
        if self._start_time:
            self._checkpoints.append((name, datetime.now()))
    
    def stop(self) -> timedelta:
        """Stop timing and return total duration.
        
        Returns:
            Total operation duration.
        """
        self._end_time = datetime.now()
        if self._start_time:
            return self._end_time - self._start_time
        return timedelta(0)
    
    def get_duration(self) -> Optional[timedelta]:
        """Get current or total duration.
        
        Returns:
            Duration since start, or None if not started.
        """
        if not self._start_time:
            return None
        
        end_time = self._end_time or datetime.now()
        return end_time - self._start_time
    
    def get_checkpoint_durations(self) -> List[Tuple[str, timedelta]]:
        """Get durations for each checkpoint.
        
        Returns:
            List of (checkpoint_name, duration_from_start) tuples.
        """
        if not self._start_time:
            return []
        
        durations = []
        for name, checkpoint_time in self._checkpoints:
            duration = checkpoint_time - self._start_time
            durations.append((name, duration))
        
        return durations
    
    def estimate_remaining(self, current_progress: int, total_progress: int) -> Optional[timedelta]:
        """Estimate remaining time based on current progress.
        
        Args:
            current_progress: Current progress value.
            total_progress: Total expected progress.
            
        Returns:
            Estimated remaining time, or None if cannot estimate.
        """
        if not self._start_time or current_progress <= 0 or total_progress <= current_progress:
            return None
        
        elapsed = datetime.now() - self._start_time
        progress_ratio = current_progress / total_progress
        
        if progress_ratio > 0:
            estimated_total = elapsed / progress_ratio
            remaining = estimated_total - elapsed
            return max(remaining, timedelta(0))
        
        return None


class BatchProgressManager:
    """Progress manager for batch operations with multiple phases."""
    
    def __init__(self, progress_manager: ProgressManager) -> None:
        """Initialize batch progress manager.
        
        Args:
            progress_manager: Base progress manager to use.
        """
        self._progress_manager = progress_manager
        self._phases: List[Tuple[str, int]] = []
        self._current_phase = 0
        self._phase_progress = 0
        self._total_items = 0
        self._completed_items = 0
    
    def add_phase(self, name: str, item_count: int) -> None:
        """Add a phase to the batch operation.
        
        Args:
            name: Name of the phase.
            item_count: Number of items in this phase.
        """
        self._phases.append((name, item_count))
        self._total_items += item_count
    
    def start_batch(self, description: str) -> None:
        """Start the batch operation.
        
        Args:
            description: Overall description of the batch operation.
        """
        self._progress_manager.start_operation(description)
        self._current_phase = 0
        self._phase_progress = 0
        self._completed_items = 0
    
    def start_phase(self, phase_index: int) -> None:
        """Start a specific phase.
        
        Args:
            phase_index: Index of the phase to start.
        """
        if 0 <= phase_index < len(self._phases):
            self._current_phase = phase_index
            self._phase_progress = 0
            
            phase_name, _ = self._phases[phase_index]
            self._progress_manager.update_status(f"Starting phase: {phase_name}", "info")
    
    def update_phase_progress(self, items_completed: int) -> None:
        """Update progress within the current phase.
        
        Args:
            items_completed: Number of items completed in current phase.
        """
        if self._current_phase < len(self._phases):
            phase_name, phase_total = self._phases[self._current_phase]
            
            # Update phase progress
            old_phase_progress = self._phase_progress
            self._phase_progress = min(items_completed, phase_total)
            
            # Update overall progress
            progress_delta = self._phase_progress - old_phase_progress
            self._completed_items += progress_delta
            
            # Show progress
            overall_progress = (self._completed_items / self._total_items) * 100
            phase_progress = (self._phase_progress / phase_total) * 100
            
            description = f"{phase_name} ({phase_progress:.1f}%) - Overall: {overall_progress:.1f}%"
            self._progress_manager.show_progress(
                self._completed_items, 
                self._total_items, 
                description
            )
    
    def complete_phase(self) -> None:
        """Complete the current phase."""
        if self._current_phase < len(self._phases):
            phase_name, phase_total = self._phases[self._current_phase]
            
            # Ensure phase is fully completed
            if self._phase_progress < phase_total:
                self.update_phase_progress(phase_total)
            
            self._progress_manager.update_status(f"Completed phase: {phase_name}", "success")
    
    def complete_batch(self, success: bool, message: str) -> None:
        """Complete the entire batch operation.
        
        Args:
            success: Whether the batch completed successfully.
            message: Completion message.
        """
        self._progress_manager.complete_operation(success, message)
        
        # Show summary
        if success:
            stats = {
                "Total Phases": len(self._phases),
                "Total Items Processed": self._completed_items,
                "Success Rate": "100%"
            }
            self._progress_manager.show_summary_statistics(stats, "Batch Operation Summary")