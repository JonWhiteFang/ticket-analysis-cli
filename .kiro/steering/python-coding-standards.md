---
inclusion: fileMatch
fileMatchPattern: '*.py'
---

# Python Coding Standards

## Python 3.7 Compatibility
- Use `from __future__ import annotations` for forward compatibility
- Avoid Python 3.8+ features (walrus operator, positional-only parameters)
- Include type hints for all functions and classes

## Code Structure
```python
from __future__ import annotations
from typing import Dict, List, Optional
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

## Import Organization
```python
# Standard library
import os
import sys

# Third-party
import click
import pandas as pd

# Local
from .models import TicketData
```

## Error Handling
```python
class TicketAnalysisError(Exception):
    """Base exception for ticket analysis."""
    pass

class AuthenticationError(TicketAnalysisError):
    """Authentication failure."""
    pass
```

## Formatting Standards
- Black formatter (line length 88)
- flake8 linting (ignore E203, W503)
- isort for import sorting
- Double quotes for strings