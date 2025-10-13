#!/usr/bin/env python3
"""Simple runner script for the ticket analyzer CLI.

This script provides a direct way to run the ticket analyzer CLI
without going through the complex application initialization that
may have dependency issues.
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Run the ticket analyzer CLI directly."""
    try:
        from ticket_analyzer.cli.main import cli
        cli()
    except Exception as e:
        print(f"Error running ticket analyzer: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()