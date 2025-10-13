"""Main entry point for ticket analyzer when run as module.

This allows the application to be executed using:
python -m ticket_analyzer
"""

from __future__ import annotations

if __name__ == "__main__":
    from .cli.main import main
    main()