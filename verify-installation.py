#!/usr/bin/env python3
"""Verification script for ticket-analyzer installation."""

import sys
import subprocess
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"Testing {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description}: PASSED")
            return True
        else:
            print(f"❌ {description}: FAILED")
            print(f"   Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ {description}: ERROR - {e}")
        return False

def main():
    """Run installation verification tests."""
    print("🔍 Verifying ticket-analyzer installation...\n")
    
    tests = [
        ("python3 --version", "Python 3 availability"),
        ("python3 -c 'import click, pandas, tqdm; print(\"Dependencies OK\")'", "Required dependencies"),
        ("python3 -m ticket_analyzer.cli.main --version", "CLI module execution"),
        ("./ticket-analyzer --version", "Wrapper script execution"),
        ("./ticket-analyzer --help", "CLI help system"),
        ("./ticket-analyzer analyze --help", "Analyze command help"),
    ]
    
    passed = 0
    total = len(tests)
    
    for cmd, description in tests:
        if run_command(cmd, description):
            passed += 1
        print()
    
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Installation verification completed successfully!")
        print("\nYou can now use the ticket-analyzer CLI:")
        print("  ./ticket-analyzer --help")
        print("  ./ticket-analyzer analyze --help")
    else:
        print("⚠️  Some tests failed. Please check the installation steps.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())