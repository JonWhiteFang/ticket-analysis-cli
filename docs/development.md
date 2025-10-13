# Development Guide

## Overview

This guide provides comprehensive information for developers working on the Ticket Analysis CLI tool. It covers development environment setup, coding standards, debugging techniques, and contribution guidelines.

## Development Environment Setup

### Prerequisites

- **Python 3.7+**: Required for application development
- **Node.js 16+**: Required for MCP components
- **Git**: Version control
- **IDE/Editor**: VS Code, PyCharm, or similar with Python support

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/org/ticket-analyzer.git
cd ticket-analyzer

# Create virtual environment
python3.7 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Install the package in development mode
pip install -e .

# Verify installation
ticket-analyzer --version
```

### IDE Configuration

#### VS Code Settings

```json
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length=88"],
    "python.sortImports.args": ["--profile", "black"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests"
    ],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        ".pytest_cache": true,
        ".coverage": true,
        "htmlcov": true
    }
}
```

#### PyCharm Configuration

1. **Interpreter Setup**:
   - File → Settings → Project → Python Interpreter
   - Add interpreter from `./venv/bin/python`

2. **Code Style**:
   - File → Settings → Editor → Code Style → Python
   - Set line length to 88
   - Enable "Black" formatter

3. **Testing**:
   - File → Settings → Tools → Python Integrated Tools
   - Set default test runner to "pytest"

### Environment Variables

```bash
# Development environment variables
export TICKET_ANALYZER_ENV=development
export TICKET_ANALYZER_LOG_LEVEL=DEBUG
export TICKET_ANALYZER_CONFIG_DIR=~/.ticket-analyzer-dev
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Optional: Enable debug mode
export TICKET_ANALYZER_DEBUG=true
```#
# Coding Standards and Guidelines

### Python Code Style

#### PEP 8 Compliance with Black

```python
# Example of properly formatted code
from __future__ import annotations

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

import click
import pandas as pd

from ticket_analyzer.models.ticket import Ticket, TicketStatus
from ticket_analyzer.models.exceptions import ValidationError


@dataclass
class AnalysisResult:
    """Analysis result with comprehensive metrics."""
    
    metrics: Dict[str, Any]
    ticket_count: int
    generated_at: datetime
    
    def __post_init__(self) -> None:
        """Validate analysis result after initialization."""
        if self.ticket_count < 0:
            raise ValidationError("Ticket count cannot be negative")


class TicketAnalyzer:
    """Analyze tickets with configurable strategies."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self._config = config or {}
        self._calculators: List[MetricsCalculator] = []
    
    def analyze(self, tickets: List[Ticket]) -> AnalysisResult:
        """Analyze tickets and return comprehensive results."""
        if not tickets:
            return AnalysisResult(
                metrics={},
                ticket_count=0,
                generated_at=datetime.now()
            )
        
        # Process tickets with validation
        validated_tickets = self._validate_tickets(tickets)
        
        # Calculate metrics
        metrics = self._calculate_metrics(validated_tickets)
        
        return AnalysisResult(
            metrics=metrics,
            ticket_count=len(validated_tickets),
            generated_at=datetime.now()
        )
    
    def _validate_tickets(self, tickets: List[Ticket]) -> List[Ticket]:
        """Validate ticket data before processing."""
        valid_tickets = []
        
        for ticket in tickets:
            try:
                # Validate required fields
                if not ticket.id or not ticket.title:
                    continue
                
                # Validate status
                if ticket.status not in TicketStatus:
                    continue
                
                valid_tickets.append(ticket)
                
            except Exception as e:
                # Log validation error but continue processing
                logger.warning(f"Invalid ticket {ticket.id}: {e}")
        
        return valid_tickets
```

#### Type Hints and Documentation

```python
from typing import Protocol, TypeVar, Generic, Union, Literal
from abc import ABC, abstractmethod

T = TypeVar('T')

class Repository(Protocol, Generic[T]):
    """Generic repository protocol for data access."""
    
    def find_by_id(self, entity_id: str) -> Optional[T]:
        """Find entity by ID.
        
        Args:
            entity_id: Unique identifier for the entity
            
        Returns:
            Entity if found, None otherwise
            
        Raises:
            RepositoryError: If data access fails
        """
        ...
    
    def find_all(self, filters: Optional[Dict[str, Any]] = None) -> List[T]:
        """Find all entities matching filters.
        
        Args:
            filters: Optional filters to apply
            
        Returns:
            List of matching entities
            
        Raises:
            RepositoryError: If data access fails
        """
        ...

class TicketRepository(Repository[Ticket]):
    """Repository for ticket data access."""
    
    def find_by_status(self, status: TicketStatus) -> List[Ticket]:
        """Find tickets by status.
        
        Args:
            status: Ticket status to filter by
            
        Returns:
            List of tickets with matching status
            
        Example:
            >>> repo = TicketRepository()
            >>> open_tickets = repo.find_by_status(TicketStatus.OPEN)
            >>> len(open_tickets)
            42
        """
        return self.find_all({"status": status.value})
```

### Error Handling Patterns

```python
# Custom exception hierarchy
class TicketAnalysisError(Exception):
    """Base exception for ticket analysis operations."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

class ValidationError(TicketAnalysisError):
    """Raised when data validation fails."""
    pass

class AuthenticationError(TicketAnalysisError):
    """Raised when authentication fails."""
    pass

# Error handling decorator
def handle_errors(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator for consistent error handling."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return func(*args, **kwargs)
        except ValidationError:
            # Re-raise validation errors as-is
            raise
        except AuthenticationError:
            # Re-raise auth errors as-is
            raise
        except Exception as e:
            # Wrap unexpected errors
            logger.exception(f"Unexpected error in {func.__name__}")
            raise TicketAnalysisError(
                f"Unexpected error in {func.__name__}: {e}",
                details={"function": func.__name__, "args": args, "kwargs": kwargs}
            ) from e
    
    return wrapper

# Usage example
@handle_errors
def process_tickets(tickets: List[Dict[str, Any]]) -> List[Ticket]:
    """Process raw ticket data into Ticket objects."""
    processed_tickets = []
    
    for ticket_data in tickets:
        try:
            ticket = Ticket.from_dict(ticket_data)
            processed_tickets.append(ticket)
        except ValidationError as e:
            logger.warning(f"Skipping invalid ticket: {e}")
            continue
    
    return processed_tickets
```## Deb
ugging and Troubleshooting

### Debugging Configuration

#### Debug Mode Setup

```python
# ticket_analyzer/debug.py
import logging
import sys
from typing import Any, Dict
from pathlib import Path

def setup_debug_logging(log_level: str = "DEBUG") -> None:
    """Setup debug logging configuration."""
    
    # Create debug log directory
    debug_dir = Path.home() / ".ticket-analyzer" / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(debug_dir / "debug.log")
        ]
    )
    
    # Set specific logger levels
    logging.getLogger('ticket_analyzer').setLevel(logging.DEBUG)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

def debug_function_calls(func):
    """Decorator to debug function calls."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} returned: {type(result)}")
            return result
        except Exception as e:
            logger.debug(f"{func.__name__} raised {type(e).__name__}: {e}")
            raise
    
    return wrapper

# Usage
import os
if os.getenv('TICKET_ANALYZER_DEBUG'):
    setup_debug_logging()
```

#### Interactive Debugging

```python
# Debug utilities
def debug_ticket_data(tickets: List[Ticket]) -> None:
    """Debug ticket data interactively."""
    import pdb; pdb.set_trace()
    
    print(f"Total tickets: {len(tickets)}")
    
    if tickets:
        sample_ticket = tickets[0]
        print(f"Sample ticket: {sample_ticket}")
        
        # Analyze ticket distribution
        status_counts = {}
        for ticket in tickets:
            status = ticket.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"Status distribution: {status_counts}")

def debug_analysis_result(result: AnalysisResult) -> None:
    """Debug analysis results."""
    print(f"Analysis Result Debug:")
    print(f"  Ticket Count: {result.ticket_count}")
    print(f"  Generated At: {result.generated_at}")
    print(f"  Metrics Keys: {list(result.metrics.keys())}")
    
    for key, value in result.metrics.items():
        print(f"  {key}: {type(value)} = {value}")

# Conditional debugging
def conditional_debug(condition: bool, message: str, **context) -> None:
    """Debug only when condition is met."""
    if condition and os.getenv('TICKET_ANALYZER_DEBUG'):
        logger = logging.getLogger(__name__)
        logger.debug(f"DEBUG: {message}")
        
        for key, value in context.items():
            logger.debug(f"  {key}: {value}")
```

### Performance Profiling

#### CPU Profiling

```python
# ticket_analyzer/profiling.py
import cProfile
import pstats
import io
from functools import wraps
from typing import Callable, Any

def profile_function(func: Callable) -> Callable:
    """Decorator to profile function execution."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not os.getenv('TICKET_ANALYZER_PROFILE'):
            return func(*args, **kwargs)
        
        profiler = cProfile.Profile()
        profiler.enable()
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            profiler.disable()
            
            # Save profile results
            profile_dir = Path.home() / ".ticket-analyzer" / "profiles"
            profile_dir.mkdir(parents=True, exist_ok=True)
            
            profile_file = profile_dir / f"{func.__name__}_{int(time.time())}.prof"
            profiler.dump_stats(str(profile_file))
            
            # Print summary
            s = io.StringIO()
            ps = pstats.Stats(profiler, stream=s)
            ps.sort_stats('cumulative')
            ps.print_stats(20)
            
            logger = logging.getLogger(__name__)
            logger.info(f"Profile for {func.__name__}:\n{s.getvalue()}")
    
    return wrapper

# Memory profiling
def profile_memory(func: Callable) -> Callable:
    """Decorator to profile memory usage."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not os.getenv('TICKET_ANALYZER_PROFILE_MEMORY'):
            return func(*args, **kwargs)
        
        import tracemalloc
        import psutil
        import os
        
        # Start memory tracing
        tracemalloc.start()
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # Get memory statistics
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_diff = final_memory - initial_memory
            
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            logger = logging.getLogger(__name__)
            logger.info(f"Memory profile for {func.__name__}:")
            logger.info(f"  Memory change: {memory_diff:.2f} MB")
            logger.info(f"  Peak traced memory: {peak / 1024 / 1024:.2f} MB")
    
    return wrapper
```

### Common Debugging Scenarios

#### Authentication Issues

```python
def debug_authentication():
    """Debug authentication problems."""
    from ticket_analyzer.auth.midway_auth import MidwayAuthenticator
    
    print("=== Authentication Debug ===")
    
    # Check environment
    import os
    auth_vars = ['KRB5_CONFIG', 'KRB5CCNAME', 'MIDWAY_CONFIG']
    for var in auth_vars:
        value = os.getenv(var, 'Not set')
        print(f"{var}: {value}")
    
    # Test mwinit availability
    import subprocess
    try:
        result = subprocess.run(['mwinit', '--version'], 
                              capture_output=True, text=True, timeout=10)
        print(f"mwinit available: {result.returncode == 0}")
        if result.returncode != 0:
            print(f"mwinit error: {result.stderr}")
    except Exception as e:
        print(f"mwinit not available: {e}")
    
    # Test authentication
    try:
        authenticator = MidwayAuthenticator()
        is_auth = authenticator.is_authenticated()
        print(f"Currently authenticated: {is_auth}")
        
        if not is_auth:
            print("Attempting authentication...")
            success = authenticator.authenticate()
            print(f"Authentication successful: {success}")
    
    except Exception as e:
        print(f"Authentication error: {e}")
        import traceback
        traceback.print_exc()
```

#### MCP Connection Issues

```python
def debug_mcp_connection():
    """Debug MCP connection problems."""
    from ticket_analyzer.external.mcp_client import MCPClient
    
    print("=== MCP Connection Debug ===")
    
    # Check Node.js availability
    import subprocess
    try:
        result = subprocess.run(['node', '--version'], 
                              capture_output=True, text=True, timeout=10)
        print(f"Node.js version: {result.stdout.strip()}")
    except Exception as e:
        print(f"Node.js not available: {e}")
    
    # Test MCP client
    try:
        client = MCPClient()
        print("MCP client created successfully")
        
        # Test connection
        # client.connect()  # Uncomment when implemented
        print("MCP connection test completed")
        
    except Exception as e:
        print(f"MCP connection error: {e}")
        import traceback
        traceback.print_exc()
```## Dev
elopment Workflow

### Git Workflow

#### Branch Naming Convention

```bash
# Feature branches
feature/ticket-analysis-metrics
feature/mcp-integration-improvements
feature/cli-enhancements

# Bug fix branches
bugfix/authentication-timeout
bugfix/data-sanitization-issue
bugfix/memory-leak-analysis

# Hotfix branches (for production issues)
hotfix/security-vulnerability-fix
hotfix/critical-auth-bug

# Release branches
release/v1.0.0
release/v1.1.0
```

#### Commit Message Format

```bash
# Format: <type>[optional scope]: <description>
# 
# [optional body]
# 
# [optional footer(s)]

# Examples:
feat(auth): add Midway authentication support

Implement secure authentication flow with:
- Session management
- Automatic re-authentication  
- Timeout handling

Closes #45

fix(cli): resolve argument parsing issue

The --output flag was not properly handling file paths
with spaces. Updated argument parser to handle quoted paths.

Fixes #67

docs(readme): update installation instructions

Add Python 3.7 requirement and virtual environment setup
instructions for better onboarding experience.

test(models): add comprehensive ticket model tests

- Test ticket creation and validation
- Test resolution time calculations
- Add edge case coverage for date handling

refactor(analysis): improve metrics calculation performance

Optimize pandas operations and reduce memory usage
by 30% for large datasets.

chore(deps): update dependencies to latest versions

Update pandas to 1.5.3 and click to 8.1.0 for security
patches and performance improvements.
```

#### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: debug-statements

  - repo: https://github.com/psf/black
    rev: 22.12.0
    hooks:
      - id: black
        language_version: python3.7

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203,W503]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v0.991
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.4
    hooks:
      - id: bandit
        args: ["-c", "pyproject.toml"]
```

### Development Scripts

#### Makefile for Common Tasks

```makefile
# Makefile
.PHONY: help install test lint format clean build docs

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install development dependencies
	pip install -r requirements-dev.txt
	pip install -e .
	pre-commit install

test:  ## Run all tests
	pytest

test-unit:  ## Run unit tests only
	pytest -m unit

test-integration:  ## Run integration tests only
	pytest -m integration

test-coverage:  ## Run tests with coverage report
	pytest --cov=ticket_analyzer --cov-report=html --cov-report=term-missing

lint:  ## Run linting checks
	flake8 ticket_analyzer tests
	mypy ticket_analyzer
	bandit -r ticket_analyzer

format:  ## Format code with black and isort
	black ticket_analyzer tests
	isort ticket_analyzer tests

clean:  ## Clean up build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

build:  ## Build package
	python -m build

docs:  ## Generate documentation
	cd docs && make html

dev-setup:  ## Complete development environment setup
	make install
	make test
	make lint
	@echo "Development environment ready!"

ci-check:  ## Run all CI checks locally
	make lint
	make test-coverage
	@echo "All CI checks passed!"
```

#### Development Scripts

```bash
#!/bin/bash
# scripts/dev-setup.sh
set -e

echo "Setting up development environment..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.7"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 7) else 1)"; then
    echo "Error: Python 3.7+ required, found $python_version"
    exit 1
fi

# Check Node.js version
if command -v node >/dev/null 2>&1; then
    node_version=$(node --version | sed 's/v//')
    echo "Node.js version: $node_version"
else
    echo "Warning: Node.js not found. MCP features may not work."
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -e .

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
pre-commit install

# Create development config
echo "Creating development configuration..."
mkdir -p ~/.ticket-analyzer-dev
cat > ~/.ticket-analyzer-dev/config.json << EOF
{
  "authentication": {
    "timeout_seconds": 60,
    "max_retry_attempts": 3
  },
  "output": {
    "default_format": "table",
    "max_results": 100
  },
  "logging": {
    "level": "DEBUG",
    "sanitize_logs": true
  }
}
EOF

# Run initial tests
echo "Running initial tests..."
pytest -x

echo "Development environment setup complete!"
echo "Activate with: source venv/bin/activate"
```