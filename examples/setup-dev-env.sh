#!/bin/bash

# Development Environment Setup Script
# Sets up a complete development environment for the Ticket Analysis CLI
#
# Usage: ./setup-dev-env.sh [OPTIONS]
# Options:
#   --full              Full setup including all dependencies
#   --minimal           Minimal setup for basic development
#   --test-only         Setup only test environment
#   --clean             Clean existing development setup
#   --help              Show this help

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEV_DIR="$HOME/.ticket-analyzer-dev"
VENV_DIR="$DEV_DIR/venv"
CONFIG_DIR="$DEV_DIR/config"
LOGS_DIR="$DEV_DIR/logs"
REPORTS_DIR="$DEV_DIR/reports"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

show_help() {
    cat << EOF
Development Environment Setup Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --full              Full setup including all dependencies and tools
    --minimal           Minimal setup for basic development
    --test-only         Setup only test environment
    --clean             Clean existing development setup
    --help              Show this help message

SETUP INCLUDES:
    - Python virtual environment with all dependencies
    - Development configuration files
    - Pre-commit hooks and linting tools
    - Test data and mock services
    - Development scripts and utilities
    - IDE configuration files

REQUIREMENTS:
    - Python 3.7 or higher
    - Node.js 16 or higher (for MCP components)
    - Git (for pre-commit hooks)

EXAMPLES:
    # Full development setup
    $0 --full

    # Quick minimal setup
    $0 --minimal

    # Clean and reset environment
    $0 --clean && $0 --full

EOF
}

check_system_requirements() {
    log_info "Checking system requirements..."
    
    # Check Python version
    if command -v python3 &> /dev/null; then
        local python_version=$(python3 --version | cut -d' ' -f2)
        log_info "Python version: $python_version"
        
        # Check if version is 3.7 or higher
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 7) else 1)"; then
            log_success "✓ Python 3.7+ available"
        else
            log_error "Python 3.7 or higher required"
            return 1
        fi
    else
        log_error "Python 3 not found"
        return 1
    fi
    
    # Check Node.js version
    if command -v node &> /dev/null; then
        local node_version=$(node --version)
        log_info "Node.js version: $node_version"
        
        # Extract major version number
        local major_version=$(echo "$node_version" | sed 's/v\([0-9]*\).*/\1/')
        if [ "$major_version" -ge 16 ]; then
            log_success "✓ Node.js 16+ available"
        else
            log_warning "Node.js 16+ recommended (found $node_version)"
        fi
    else
        log_warning "Node.js not found (required for MCP components)"
    fi
    
    # Check Git
    if command -v git &> /dev/null; then
        log_success "✓ Git available"
    else
        log_warning "Git not found (required for pre-commit hooks)"
    fi
    
    return 0
}

create_directory_structure() {
    log_info "Creating development directory structure..."
    
    mkdir -p "$DEV_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$LOGS_DIR"
    mkdir -p "$REPORTS_DIR"
    mkdir -p "$DEV_DIR/test-data"
    mkdir -p "$DEV_DIR/scripts"
    mkdir -p "$DEV_DIR/mock-services"
    
    log_success "Directory structure created at $DEV_DIR"
}

setup_python_environment() {
    log_info "Setting up Python virtual environment..."
    
    # Create virtual environment
    python3 -m venv "$VENV_DIR"
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install development dependencies
    if [ -f "$PROJECT_ROOT/requirements-dev.txt" ]; then
        log_info "Installing development dependencies..."
        pip install -r "$PROJECT_ROOT/requirements-dev.txt"
    fi
    
    # Install main dependencies
    if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        log_info "Installing main dependencies..."
        pip install -r "$PROJECT_ROOT/requirements.txt"
    fi
    
    # Install package in development mode
    if [ -f "$PROJECT_ROOT/setup.py" ] || [ -f "$PROJECT_ROOT/pyproject.toml" ]; then
        log_info "Installing package in development mode..."
        pip install -e "$PROJECT_ROOT"
    fi
    
    log_success "Python environment setup completed"
}

create_development_configs() {
    log_info "Creating development configuration files..."
    
    # Copy development config
    if [ -f "$SCRIPT_DIR/dev-config.json" ]; then
        cp "$SCRIPT_DIR/dev-config.json" "$CONFIG_DIR/config.json"
        log_success "Development config copied"
    fi
    
    # Create environment file
    cat > "$DEV_DIR/.env" << EOF
# Development Environment Variables
TICKET_ANALYZER_CONFIG_DIR=$CONFIG_DIR
TICKET_ANALYZER_LOG_LEVEL=DEBUG
TICKET_ANALYZER_MAX_RESULTS=50
TICKET_ANALYZER_TIMEOUT=30

# Development flags
TICKET_ANALYZER_DEV_MODE=true
TICKET_ANALYZER_MOCK_MCP=false
TICKET_ANALYZER_SKIP_AUTH=false

# Paths
TICKET_ANALYZER_REPORTS_DIR=$REPORTS_DIR
TICKET_ANALYZER_LOGS_DIR=$LOGS_DIR
EOF
    
    # Create activation script
    cat > "$DEV_DIR/activate.sh" << EOF
#!/bin/bash
# Development environment activation script

echo "Activating Ticket Analysis CLI development environment..."

# Activate Python virtual environment
source "$VENV_DIR/bin/activate"

# Set environment variables
export TICKET_ANALYZER_CONFIG_DIR="$CONFIG_DIR"
export TICKET_ANALYZER_LOG_LEVEL="DEBUG"
export TICKET_ANALYZER_DEV_MODE="true"

# Add development scripts to PATH
export PATH="$DEV_DIR/scripts:\$PATH"

# Set prompt to indicate dev environment
export PS1="(ticket-analyzer-dev) \$PS1"

echo "Development environment activated!"
echo "Config directory: $CONFIG_DIR"
echo "Logs directory: $LOGS_DIR"
echo "Reports directory: $REPORTS_DIR"
echo ""
echo "Quick commands:"
echo "  ticket-analyzer --help"
echo "  pytest"
echo "  pre-commit run --all-files"
echo ""
echo "To deactivate: deactivate"
EOF
    
    chmod +x "$DEV_DIR/activate.sh"
    
    log_success "Development configuration created"
}

setup_pre_commit_hooks() {
    log_info "Setting up pre-commit hooks..."
    
    if ! command -v pre-commit &> /dev/null; then
        log_info "Installing pre-commit..."
        pip install pre-commit
    fi
    
    # Install pre-commit hooks if config exists
    if [ -f "$PROJECT_ROOT/.pre-commit-config.yaml" ]; then
        cd "$PROJECT_ROOT"
        pre-commit install
        log_success "Pre-commit hooks installed"
    else
        log_warning "No .pre-commit-config.yaml found, skipping pre-commit setup"
    fi
}

create_development_scripts() {
    log_info "Creating development scripts..."
    
    # Quick test script
    cat > "$DEV_DIR/scripts/quick-test.sh" << 'EOF'
#!/bin/bash
# Quick test script for development

echo "Running quick tests..."

# Activate environment
source "$HOME/.ticket-analyzer-dev/activate.sh"

# Run basic tests
echo "1. Testing CLI availability..."
ticket-analyzer --version

echo "2. Testing configuration..."
ticket-analyzer config show

echo "3. Running unit tests..."
pytest tests/unit/ -v --tb=short

echo "4. Running linting..."
flake8 ticket_analyzer tests --count --statistics

echo "Quick tests completed!"
EOF
    
    # Mock data generator
    cat > "$DEV_DIR/scripts/generate-mock-data.py" << 'EOF'
#!/usr/bin/env python3
"""Generate mock ticket data for development and testing."""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

def generate_mock_tickets(count=100):
    """Generate mock ticket data."""
    statuses = ["Open", "In Progress", "Resolved", "Closed"]
    severities = ["SEV_1", "SEV_2", "SEV_3", "SEV_4", "SEV_5"]
    teams = ["Frontend Team", "Backend Team", "DevOps", "QA Team"]
    assignees = ["alice", "bob", "charlie", "diana", "eve"]
    
    tickets = []
    
    for i in range(count):
        created_date = datetime.now() - timedelta(days=random.randint(1, 90))
        
        ticket = {
            "id": f"T{1000000 + i}",
            "title": f"Sample ticket {i+1}",
            "description": f"This is a mock ticket for development and testing purposes. Ticket number {i+1}.",
            "status": random.choice(statuses),
            "severity": random.choice(severities),
            "created_date": created_date.isoformat(),
            "updated_date": (created_date + timedelta(hours=random.randint(1, 48))).isoformat(),
            "assignee": random.choice(assignees),
            "resolver_group": random.choice(teams),
            "tags": random.sample(["bug", "feature", "improvement", "urgent", "documentation"], k=random.randint(0, 3))
        }
        
        # Add resolved date for resolved/closed tickets
        if ticket["status"] in ["Resolved", "Closed"]:
            ticket["resolved_date"] = (created_date + timedelta(hours=random.randint(1, 168))).isoformat()
        
        tickets.append(ticket)
    
    return tickets

if __name__ == "__main__":
    mock_data = generate_mock_tickets(100)
    
    output_file = Path.home() / ".ticket-analyzer-dev" / "test-data" / "mock-tickets.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(mock_data, f, indent=2)
    
    print(f"Generated {len(mock_data)} mock tickets in {output_file}")
EOF
    
    # Make scripts executable
    chmod +x "$DEV_DIR/scripts"/*.sh
    chmod +x "$DEV_DIR/scripts"/*.py
    
    log_success "Development scripts created"
}

setup_ide_configuration() {
    log_info "Setting up IDE configuration..."
    
    # VS Code settings
    if [ -d "$PROJECT_ROOT/.vscode" ] || [ -d "$HOME/.vscode" ]; then
        mkdir -p "$PROJECT_ROOT/.vscode"
        
        cat > "$PROJECT_ROOT/.vscode/settings.json" << EOF
{
    "python.defaultInterpreterPath": "$VENV_DIR/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.mypyEnabled": true,
    "python.formatting.provider": "black",
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
        "**/.pytest_cache": true,
        "**/.mypy_cache": true,
        "**/venv": true
    }
}
EOF
        
        log_success "VS Code configuration created"
    fi
}

run_initial_tests() {
    log_info "Running initial tests..."
    
    # Activate environment
    source "$VENV_DIR/bin/activate"
    
    # Test CLI installation
    if ticket-analyzer --version &> /dev/null; then
        log_success "✓ CLI installation verified"
    else
        log_warning "⚠ CLI not available in PATH"
    fi
    
    # Run basic tests if available
    if [ -d "$PROJECT_ROOT/tests" ]; then
        log_info "Running test suite..."
        if pytest "$PROJECT_ROOT/tests" --tb=short -q; then
            log_success "✓ Tests passed"
        else
            log_warning "⚠ Some tests failed"
        fi
    fi
    
    # Generate mock data
    if [ -f "$DEV_DIR/scripts/generate-mock-data.py" ]; then
        python3 "$DEV_DIR/scripts/generate-mock-data.py"
        log_success "✓ Mock data generated"
    fi
}

clean_environment() {
    log_info "Cleaning existing development environment..."
    
    if [ -d "$DEV_DIR" ]; then
        rm -rf "$DEV_DIR"
        log_success "Development environment cleaned"
    else
        log_info "No existing environment found"
    fi
}

main() {
    local setup_type="${1:---full}"
    
    case "$setup_type" in
        --full)
            log_info "Starting full development environment setup..."
            check_system_requirements
            create_directory_structure
            setup_python_environment
            create_development_configs
            setup_pre_commit_hooks
            create_development_scripts
            setup_ide_configuration
            run_initial_tests
            ;;
        --minimal)
            log_info "Starting minimal development environment setup..."
            check_system_requirements
            create_directory_structure
            setup_python_environment
            create_development_configs
            ;;
        --test-only)
            log_info "Setting up test environment only..."
            create_directory_structure
            create_development_scripts
            run_initial_tests
            ;;
        --clean)
            clean_environment
            exit 0
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $setup_type"
            show_help
            exit 1
            ;;
    esac
    
    log_success "Development environment setup completed!"
    log_info "To activate the environment, run:"
    log_info "  source $DEV_DIR/activate.sh"
    log_info ""
    log_info "Development directories:"
    log_info "  Config: $CONFIG_DIR"
    log_info "  Logs: $LOGS_DIR"
    log_info "  Reports: $REPORTS_DIR"
    log_info "  Scripts: $DEV_DIR/scripts"
}

main "$@"