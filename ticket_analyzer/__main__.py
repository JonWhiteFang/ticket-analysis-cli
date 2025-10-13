"""Main entry point for ticket analyzer when run as module.

This module provides the main entry point for the ticket analyzer application
when executed as a Python module. It handles application startup, configuration
loading, service initialization, and command routing with proper error handling
and exit codes.

Usage:
    python -m ticket_analyzer [command] [options]
    python3 -m ticket_analyzer analyze --help
"""

from __future__ import annotations
import sys
import logging
import signal
from typing import Optional, NoReturn
from pathlib import Path

from .app import TicketAnalyzerApp, create_app
from .container import create_container
from .service_integration import create_service_integrator
from .models import (
    ApplicationConfig,
    ConfigurationError,
    AuthenticationError,
    TicketAnalysisError
)
from .config import ConfigurationManager
from .cli.utils import error_message, success_message, info_message
from .cli.signals import GracefulShutdown

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration for the application.
    
    Args:
        verbose: Enable verbose logging if True.
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stderr)
        ]
    )
    
    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


def load_application_config(config_file: Optional[str] = None) -> ApplicationConfig:
    """Load application configuration from various sources.
    
    Args:
        config_file: Optional path to configuration file.
        
    Returns:
        Loaded application configuration.
        
    Raises:
        ConfigurationError: If configuration loading fails.
    """
    try:
        # Set config file in environment if provided
        if config_file:
            import os
            os.environ['TICKET_ANALYZER_CONFIG_FILE'] = config_file
        
        config_manager = ConfigurationManager()
        config_data = config_manager.load_config()
        
        return ApplicationConfig.from_dict(config_data)
        
    except Exception as e:
        raise ConfigurationError(f"Failed to load configuration: {e}")


def create_and_initialize_app(config: ApplicationConfig) -> TicketAnalyzerApp:
    """Create and initialize the application with all services.
    
    Args:
        config: Application configuration.
        
    Returns:
        Initialized application instance.
        
    Raises:
        ConfigurationError: If application initialization fails.
    """
    try:
        # Create dependency container
        container = create_container(config)
        
        # Create service integrator and wire services
        integrator = create_service_integrator(container, config)
        integrator.wire_services()
        integrator.initialize_services()
        
        # Create and initialize application
        app = create_app(config)
        app.initialize()
        
        return app
        
    except Exception as e:
        logger.error(f"Application initialization failed: {e}")
        raise ConfigurationError(f"Failed to initialize application: {e}")


def handle_application_error(error: Exception) -> int:
    """Handle application errors and return appropriate exit code.
    
    Args:
        error: The error that occurred.
        
    Returns:
        Exit code for the application.
    """
    if isinstance(error, AuthenticationError):
        error_message(f"Authentication failed: {error}")
        error_message("Please run 'mwinit -o' to authenticate and try again.")
        return 2
    
    elif isinstance(error, ConfigurationError):
        error_message(f"Configuration error: {error}")
        error_message("Please check your configuration and try again.")
        return 3
    
    elif isinstance(error, TicketAnalysisError):
        error_message(f"Analysis error: {error}")
        return 4
    
    else:
        error_message(f"Unexpected error: {error}")
        logger.exception("Unexpected error occurred")
        return 1


def setup_signal_handlers() -> GracefulShutdown:
    """Setup signal handlers for graceful shutdown.
    
    Returns:
        GracefulShutdown handler instance.
    """
    shutdown_handler = GracefulShutdown()
    
    def signal_handler(signum: int, frame) -> None:
        """Handle shutdown signals."""
        signal_name = signal.Signals(signum).name
        info_message(f"Received {signal_name}, shutting down gracefully...")
        shutdown_handler.shutdown = True
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    return shutdown_handler


def main() -> NoReturn:
    """Main entry point for the ticket analyzer application.
    
    This function handles the complete application lifecycle including:
    - Configuration loading
    - Service initialization
    - Command routing
    - Error handling
    - Graceful shutdown
    
    Exit codes:
        0: Success
        1: General error
        2: Authentication error
        3: Configuration error
        4: Analysis error
    """
    app: Optional[TicketAnalyzerApp] = None
    exit_code = 0
    
    try:
        # Setup signal handlers
        shutdown_handler = setup_signal_handlers()
        
        # Parse basic CLI arguments to get config file and verbose flag
        verbose = "--verbose" in sys.argv or "-v" in sys.argv
        
        # Setup logging early
        setup_logging(verbose)
        
        logger.info("Starting ticket analyzer application")
        
        # Find config file from CLI args
        config_file = None
        if "--config" in sys.argv:
            config_index = sys.argv.index("--config")
            if config_index + 1 < len(sys.argv):
                config_file = sys.argv[config_index + 1]
        elif "-c" in sys.argv:
            config_index = sys.argv.index("-c")
            if config_index + 1 < len(sys.argv):
                config_file = sys.argv[config_index + 1]
        
        # Load configuration
        config = load_application_config(config_file)
        
        # Create and initialize application
        app = create_and_initialize_app(config)
        
        # Check if shutdown was requested during initialization
        if shutdown_handler.shutdown:
            info_message("Shutdown requested during initialization")
            exit_code = 0
        else:
            # Import and run CLI after app is initialized
            from .cli.main import main as cli_main
            
            # Pass the initialized app to CLI
            # Note: This requires updating the CLI to accept the app instance
            try:
                cli_main()
                success_message("Application completed successfully")
                exit_code = 0
            except SystemExit as e:
                # Click raises SystemExit, capture the exit code
                exit_code = e.code or 0
            except KeyboardInterrupt:
                info_message("Operation cancelled by user")
                exit_code = 0
    
    except KeyboardInterrupt:
        info_message("Application startup cancelled by user")
        exit_code = 0
    
    except Exception as e:
        exit_code = handle_application_error(e)
    
    finally:
        # Cleanup application resources
        if app:
            try:
                logger.info("Shutting down application")
                app.shutdown()
                success_message("Application shutdown completed")
            except Exception as e:
                logger.error(f"Error during application shutdown: {e}")
                error_message(f"Shutdown error: {e}")
                if exit_code == 0:
                    exit_code = 1
        
        logger.info(f"Application exiting with code {exit_code}")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()