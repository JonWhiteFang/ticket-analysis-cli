---
inclusion: fileMatch
fileMatchPattern: '*cli*'
---

# CLI Development Standards

## Click Framework Patterns

### Basic Command Structure
```python
import click

@click.group()
@click.version_option()
@click.option('--verbose', '-v', is_flag=True)
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose

@cli.command()
@click.option('--format', '-f', type=click.Choice(['json', 'csv', 'table']), default='table')
@click.option('--output', '-o', type=click.Path())
def analyze(format: str, output: Optional[str]) -> None:
    """Analyze ticket data."""
    pass
```

### Validation and Error Handling
```python
@click.command()
@click.argument('ticket_ids', nargs=-1, required=True)
@click.option('--start-date', type=click.DateTime(['%Y-%m-%d']))
def process_tickets(ticket_ids: tuple, start_date: Optional[str]) -> None:
    if start_date and start_date > datetime.now():
        raise click.BadParameter('Start date cannot be in the future')
```

### Output Styling
```python
def success_message(msg: str) -> None:
    click.echo(click.style(msg, fg='green'))

def error_message(msg: str) -> None:
    click.echo(click.style(msg, fg='red'), err=True)

def warning_message(msg: str) -> None:
    click.echo(click.style(msg, fg='yellow'))
```

### Progress Indicators
```python
from tqdm import tqdm

def process_with_progress(items, description: str):
    with tqdm(items, desc=description) as pbar:
        for item in pbar:
            result = process_item(item)
            pbar.set_postfix({'status': 'done'})
```

### Graceful Shutdown
```python
import signal

class GracefulShutdown:
    def __init__(self):
        self.shutdown = False
        signal.signal(signal.SIGINT, self._exit_gracefully)
    
    def _exit_gracefully(self, signum, frame):
        self.shutdown = True
        click.echo(click.style('\nShutdown requested...', fg='yellow'))
```