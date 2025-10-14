---
inclusion: fileMatch
fileMatchPattern: '*.py'
---

# Python Coding Standards

## Python 3.7 Compatibility Requirements

### Version Constraints
- All code must be compatible with Python 3.7+
- Use `from __future__ import annotations` for forward compatibility
- Avoid features introduced in Python 3.8+ (walrus operator, positional-only parameters)

### Type Hinting Standards
```python
from __future__ import annotations
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass

@dataclass
class TicketData:
    id: str
    title: str
    status: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self) -> None:
        if self.tags is None:
            self.tags = []
```

### Import Organization
```python
# Standard library imports
import os
import sys
from typing import Dict, List

# Third-party imports
import click
import pandas as pd

# Local imports
from .models import TicketData
from .services import AnalysisService
```

### Dataclass Usage Patterns
- Use `@dataclass` for data containers
- Include type hints for all fields
- Use `__post_init__` for validation and default initialization
- Prefer immutable dataclasses with `frozen=True` when appropriate

### Error Handling Patterns
```python
class TicketAnalysisError(Exception):
    """Base exception for ticket analysis operations."""
    pass

class AuthenticationError(TicketAnalysisError):
    """Raised when authentication fails."""
    pass

class DataProcessingError(TicketAnalysisError):
    """Raised when data processing fails."""
    pass

# Usage
try:
    result = process_tickets(data)
except AuthenticationError as e:
    logger.error(f"Authentication failed: {e}")
    raise click.ClickException("Authentication required")
```

### Logging Standards
```python
import logging
from typing import Any, Dict

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive information from log data."""
    sensitive_keys = {'password', 'token', 'secret', 'key'}
    return {k: '***' if k.lower() in sensitive_keys else v 
            for k, v in data.items()}
```

### Code Formatting
- Use Black for code formatting with line length 88
- Use flake8 for linting with E203, W503 ignored
- Use isort for import sorting
- Maximum line length: 88 characters
- Use double quotes for strings