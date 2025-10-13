# CLI Development Standards

## Click Framework Usage Patterns

### Command Structure
```python
import click
from typing import Optional

@click.group()
@click.version_option()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """Ticket Analysis CLI Tool."""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose

@cli.command()
@click.option('--format', '-f', type=click.Choice(['json', 'csv', 'table']), 
              default='table', help='Output format')
@click.option('--output', '-o', type=click.Path(), help='Output file path')
@click.pass_context
def analyze(ctx: click.Context, format: str, output: Optional[str]) -> None:
    """Analyze ticket data."""
    pass
```

### Argument Design and Validation
```python
@click.command()
@click.argument('ticket_ids', nargs=-1, required=True)
@click.option('--start-date', type=click.DateTime(['%Y-%m-%d']), 
              help='Start date (YYYY-MM-DD)')
@click.option('--end-date', type=click.DateTime(['%Y-%m-%d']), 
              help='End date (YYYY-MM-DD)')
def process_tickets(ticket_ids: tuple, start_date: Optional[str], 
                   end_date: Optional[str]) -> None:
    """Process specific tickets."""
    if start_date and end_date and start_date > end_date:
        raise click.BadParameter('Start date must be before end date')
```

### Color-Coded Output Standards
```python
import click

def success_message(message: str) -> None:
    """Display success message in green."""
    click.echo(click.style(message, fg='green'))

def error_message(message: str) -> None:
    """Display error message in red."""
    click.echo(click.style(message, fg='red'), err=True)

def info_message(message: str) -> None:
    """Display info message in blue."""
    click.echo(click.style(message, fg='blue'))

def warning_message(message: str) -> None:
    """Display warning message in yellow."""
    click.echo(click.style(message, fg='yellow'))
```

### Progress Indicator Implementation
```python
from tqdm import tqdm
from typing import Iterable, Any

def process_with_progress(items: Iterable[Any], description: str) -> None:
    """Process items with progress bar."""
    with tqdm(items, desc=description, unit='item') as pbar:
        for item in pbar:
            # Process item
            result = process_item(item)
            pbar.set_postfix({'status': 'processed'})
```

### Signal Handling and Graceful Shutdown
```python
import signal
import sys
from typing import Any

class GracefulShutdown:
    def __init__(self) -> None:
        self.shutdown = False
        signal.signal(signal.SIGINT, self._exit_gracefully)
        signal.signal(signal.SIGTERM, self._exit_gracefully)
    
    def _exit_gracefully(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals gracefully."""
        self.shutdown = True
        click.echo(click.style('\nShutdown requested...', fg='yellow'))
        sys.exit(0)

# Usage in commands
shutdown_handler = GracefulShutdown()

@click.command()
def long_running_command() -> None:
    """Example of long-running command with graceful shutdown."""
    while not shutdown_handler.shutdown:
        # Do work
        pass
```

### Error Handling Patterns
```python
@click.command()
def command_with_error_handling() -> None:
    """Command with proper error handling."""
    try:
        # Command logic
        pass
    except AuthenticationError as e:
        error_message(f"Authentication failed: {e}")
        raise click.Abort()
    except DataProcessingError as e:
        error_message(f"Data processing failed: {e}")
        raise click.Abort()
    except Exception as e:
        error_message(f"Unexpected error: {e}")
        if click.get_current_context().obj.get('verbose'):
            import traceback
            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()
```

### Configuration File Support
```python
import configparser
from pathlib import Path

@click.command()
@click.option('--config', '-c', type=click.Path(exists=True), 
              help='Configuration file path')
def command_with_config(config: Optional[str]) -> None:
    """Command that supports configuration files."""
    if config:
        config_path = Path(config)
    else:
        config_path = Path.home() / '.ticket-analyzer' / 'config.ini'
    
    if config_path.exists():
        parser = configparser.ConfigParser()
        parser.read(config_path)
        # Use configuration
```