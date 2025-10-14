# Ticket Analysis CLI

[![CI Pipeline](https://github.com/org/ticket-analyzer/workflows/CI%20Pipeline/badge.svg)](https://github.com/org/ticket-analyzer/actions)
[![Coverage](https://codecov.io/gh/org/ticket-analyzer/branch/main/graph/badge.svg)](https://codecov.io/gh/org/ticket-analyzer)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 16+](https://img.shields.io/badge/node.js-16+-green.svg)](https://nodejs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A secure, Python 3.7-compatible CLI tool for analyzing ticket data from Amazon's internal systems using MCP (Model Context Protocol) integration. The application provides comprehensive metrics, trend analysis, and HTML reports with visualizations to help teams understand their ticket patterns and performance.

## Features

- 🎫 **Comprehensive Ticket Analysis**: Resolution time metrics, status distribution, team performance analysis
- 🔐 **Secure Authentication**: Midway integration with session management and timeout handling
- 📊 **Multiple Output Formats**: CLI tables with color coding, JSON, CSV, and rich HTML reports
- 📈 **Advanced Visualizations**: Interactive charts with matplotlib and seaborn integration
- 🛡️ **Data Sanitization**: Automatic PII detection and removal with comprehensive security measures
- 🔌 **MCP Integration**: Seamless connection to Amazon's internal ticket systems via Builder MCP
- ⚡ **Performance Optimized**: Efficient processing of large datasets with pandas DataFrames
- 🔄 **Resilience Patterns**: Circuit breaker, retry logic, and graceful error handling
- 📋 **Flexible Configuration**: Support for JSON/INI config files, environment variables, and CLI arguments
- 🧪 **Comprehensive Testing**: 80%+ code coverage with pytest framework

> **Note**: This is a development version. The CLI interface is functional and ready for use. Some advanced features are still being implemented and integrated.

## Quick Start

### Prerequisites

- **Python 3.7 or higher** - Required for all functionality
- **Node.js 16 or higher** - Required for MCP integration components
- **Access to Amazon internal network** - Required for ticket data access
- **Valid Midway credentials** - Required for authentication

### Installation

```bash
# Clone the repository
git clone https://github.com/JonWhiteFang/ticket-analysis-cli.git
cd ticket-analysis-cli

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# Install dependencies
pip3 install -r requirements.txt

# Make the CLI script executable
chmod +x ticket-analyzer

# Verify installation
./ticket-analyzer --version

# Run comprehensive verification (optional)
python3 verify-installation.py
```

### Basic Usage

```bash
# Method 1: Using the wrapper script (recommended)
./ticket-analyzer --version
./ticket-analyzer --help

# Method 2: Using Python module execution
python3 -m ticket_analyzer.cli.main --version
python3 -m ticket_analyzer.cli.main --help

# View available commands and options
./ticket-analyzer analyze --help
./ticket-analyzer config --help
./ticket-analyzer report --help

# Authenticate with Midway (required first step)
mwinit -o

# Analyze tickets with default settings (last 30 days)
./ticket-analyzer analyze

# Analyze specific tickets by ID
ticket-analyzer analyze --ticket-ids T123456 T789012 --format json

# Generate comprehensive HTML report with charts
ticket-analyzer analyze \
  --format html \
  --output report.html \
  --include-charts \
  --start-date 2024-01-01 \
  --end-date 2024-01-31

# Filter by status and severity with team performance analysis
ticket-analyzer analyze \
  --status "Open" "In Progress" \
  --severity SEV_1 SEV_2 \
  --team-performance \
  --resolver-group "My Team" \
  --verbose

# Trend analysis for last quarter with priority breakdown
ticket-analyzer analyze \
  --date-range quarter \
  --trend-analysis \
  --priority-analysis \
  --format html \
  --output quarterly-trends.html

# Search for specific issues with comprehensive analysis
ticket-analyzer analyze \
  --search-term "authentication error" \
  --tags urgent production \
  --include-resolved \
  --export-raw-data \
  --format json \
  --output auth-issues.json

# Configuration management examples
ticket-analyzer config show --format json --show-sources
ticket-analyzer config set authentication.timeout 120 --type int
ticket-analyzer config validate --strict --fix-issues

# Report management examples
ticket-analyzer report list --format-filter html --sort-by date
ticket-analyzer report convert analysis.json --format html --include-charts
ticket-analyzer report merge report1.json report2.json --output combined.html
ticket-analyzer report clean --older-than 30 --dry-run
```

### Configuration

Create a configuration file for persistent settings:

```bash
# Create config directory
mkdir -p ~/.ticket-analyzer

# Create configuration file
cat > ~/.ticket-analyzer/config.json << EOF
{
  "output": {
    "default_format": "table",
    "max_results": 1000,
    "sanitize_output": true
  },
  "authentication": {
    "timeout_seconds": 60,
    "check_interval_seconds": 300
  },
  "logging": {
    "level": "INFO",
    "sanitize_logs": true
  }
}
EOF
```

## Troubleshooting

### Command Not Found Error

If you get `zsh: command not found: ticket-analyzer`, use one of these solutions:

**Option 1: Use the wrapper script (recommended)**
```bash
# Make sure you're in the project directory
cd ticket-analysis-cli

# Make the script executable
chmod +x ticket-analyzer

# Run the CLI
./ticket-analyzer --version
```

**Option 2: Use Python module execution**
```bash
# Run directly as a Python module
python3 -m ticket_analyzer.cli.main --version
python3 -m ticket_analyzer.cli.main analyze --help
```

**Option 3: Add to PATH (optional)**
```bash
# Add the project directory to your PATH
export PATH="$PATH:$(pwd)"

# Now you can use ticket-analyzer directly
ticket-analyzer --version
```

### Common Issues

**Authentication Issues**
```bash
# Refresh Midway authentication
mwinit -o

# Check authentication status
mwinit -s
```

**Permission Errors**
```bash
# Ensure script is executable
chmod +x ticket-analyzer

# Check Python permissions
python3 --version
```

**Missing Dependencies**
```bash
# Reinstall dependencies
pip3 install -r requirements.txt

# Run verification script to check everything
python3 verify-installation.py

# Manual check for missing packages
python3 -c "import click, pandas, tqdm; print('Dependencies OK')"
```

## Documentation

- [Installation Guide](docs/installation.md) - Detailed setup instructions
- [User Guide](docs/user-guide.md) - Comprehensive usage documentation
- [CLI Reference](docs/cli-reference.md) - Complete command-line interface documentation
- [API Documentation](docs/api.md) - Developer API reference
- [Configuration Guide](docs/configuration.md) - Configuration options and examples
- [Security Guidelines](docs/security.md) - Security best practices and data handling
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions
- [Contributing](docs/contributing.md) - Development and contribution guidelines

## CLI Commands

### Main Commands

| Command | Description | Example |
|---------|-------------|---------|
| `analyze` | Analyze ticket data with comprehensive filtering | `ticket-analyzer analyze --status Open --days-back 7` |
| `config` | Manage configuration settings | `ticket-analyzer config show --format json` |
| `report` | Generate and manage analysis reports | `ticket-analyzer report list --format-filter html` |

### Analyze Command Options

#### Time Period Options
| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--start-date` | Start date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS) | 30 days ago | `--start-date 2024-01-01` |
| `--end-date` | End date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS) | today | `--end-date 2024-01-31` |
| `--days-back` | Number of days back from today (1-365) | 30 | `--days-back 7` |
| `--date-range` | Predefined ranges (today, yesterday, week, month, quarter) | none | `--date-range week` |

#### Filtering Options
| Option | Description | Example |
|--------|-------------|---------|
| `--ticket-ids` | Specific ticket IDs (multiple allowed) | `--ticket-ids T123456 T789012` |
| `--status` | Filter by status (multiple allowed) | `--status Open "In Progress" Resolved` |
| `--severity` | Filter by severity (multiple allowed) | `--severity SEV_1 SEV_2` |
| `--assignee` | Filter by assignee (multiple allowed) | `--assignee user1 user2` |
| `--resolver-group` | Filter by resolver group (multiple allowed) | `--resolver-group "Team A" "Team B"` |
| `--tags` | Filter by tags (multiple allowed) | `--tags urgent production bug` |
| `--search-term` | Search in title/description | `--search-term "authentication error"` |

#### Analysis Options
| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--include-resolved` | Include resolved tickets | false | `--include-resolved` |
| `--exclude-automated` | Exclude automated tickets | false | `--exclude-automated` |
| `--priority-analysis` | Include priority-based analysis | false | `--priority-analysis` |
| `--trend-analysis` | Include trend analysis over time | false | `--trend-analysis` |
| `--team-performance` | Include team performance metrics | false | `--team-performance` |
| `--export-raw-data` | Export raw ticket data with analysis | false | `--export-raw-data` |

#### Output Options
| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--format` | Output format (table, json, csv, html) | table | `--format json` |
| `--output` | Output file path | stdout | `--output report.html` |
| `--max-results` | Maximum results (1-10000) | 1000 | `--max-results 500` |
| `--include-charts` | Include charts in HTML reports | true | `--include-charts` |
| `--no-color` | Disable colored output | false | `--no-color` |

#### Configuration Options
| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--config-file` | Override configuration file | auto-detect | `--config-file custom.json` |
| `--timeout` | Request timeout in seconds (10-300) | 60 | `--timeout 120` |
| `--batch-size` | Batch size for processing (10-1000) | 100 | `--batch-size 50` |

#### Authentication Options
| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--auth-timeout` | Authentication timeout (30-300 seconds) | 60 | `--auth-timeout 90` |
| `--force-auth` | Force re-authentication | false | `--force-auth` |
| `--skip-auth-check` | Skip initial auth check (use with caution) | false | `--skip-auth-check` |

### Config Command Options

| Subcommand | Description | Example |
|------------|-------------|---------|
| `show` | Display current configuration | `config show --section authentication` |
| `set` | Set configuration value | `config set output_format json --type string` |
| `unset` | Remove configuration value | `config unset custom_setting` |
| `validate` | Validate configuration file | `config validate --strict --fix-issues` |
| `init` | Initialize new configuration | `config init --format json --template comprehensive` |

### Report Command Options

| Subcommand | Description | Example |
|------------|-------------|---------|
| `list` | List available reports | `report list --format-filter html --sort-by date` |
| `convert` | Convert report between formats | `report convert analysis.json --format html` |
| `merge` | Merge multiple reports | `report merge *.json --output combined.html` |
| `clean` | Clean up old reports | `report clean --older-than 7 --dry-run` |

## Project Structure

```
ticket-analyzer/
├── ticket_analyzer/          # Main package
│   ├── cli/                 # CLI commands and interface
│   │   ├── commands/        # Individual CLI commands
│   │   └── main.py         # Main CLI entry point
│   ├── models/              # Data models and entities
│   │   ├── ticket.py       # Ticket data model
│   │   ├── analysis.py     # Analysis result models
│   │   └── config.py       # Configuration models
│   ├── services/            # Business logic services
│   │   └── analysis_service.py
│   ├── repositories/        # Data access layer
│   │   └── mcp_ticket_repository.py
│   ├── external/            # External integrations
│   │   ├── mcp_client.py   # MCP client implementation
│   │   └── auth_service.py # Authentication service
│   ├── reporting/           # Report generation
│   │   ├── cli_reporter.py # CLI table reporter
│   │   └── html_reporter.py # HTML report generator
│   ├── config/              # Configuration management
│   ├── security/            # Security and sanitization
│   ├── logging/             # Logging configuration
│   └── monitoring/          # Performance monitoring
├── tests/                   # Test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── conftest.py         # Pytest configuration
├── docs/                    # Documentation
├── examples/                # Example configurations
├── templates/               # HTML report templates
├── .kiro/                   # Kiro IDE configuration
│   ├── specs/              # Feature specifications
│   └── steering/           # Development guidelines
└── requirements.txt         # Python dependencies
```

## Development

### Setup Development Environment

```bash
# Install development dependencies
pip3 install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Run linting and formatting
flake8 ticket_analyzer tests
black ticket_analyzer tests --check
isort ticket_analyzer tests --check-only
mypy ticket_analyzer

# Run security checks
bandit -r ticket_analyzer
safety check
```

### Running Tests

```bash
# Run all tests with coverage
pytest --cov=ticket_analyzer --cov-report=html

# Run specific test categories
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only
pytest -m "not slow"        # Skip slow tests

# Run tests with verbose output
pytest -v --tb=short
```

### Code Quality Standards

- **Python 3.7 Compatibility**: All code must work with Python 3.7+
- **Type Hints**: Complete type annotations using `typing` module
- **Code Coverage**: Minimum 80% coverage for core modules
- **Security**: Comprehensive input validation and data sanitization
- **Documentation**: Docstrings for all public APIs
- **Testing**: Unit and integration tests for all functionality

## Security

This tool handles sensitive ticket data and requires careful security considerations:

### Data Protection
- **Automatic PII Detection**: Removes emails, phone numbers, SSNs, and other sensitive data
- **Secure Logging**: All logs are sanitized to prevent credential exposure
- **Secure File Operations**: Temporary files use restrictive permissions (0o600)
- **Input Validation**: Comprehensive validation prevents injection attacks

### Authentication Security
- **Midway Integration**: Secure subprocess calls to `mwinit` without credential logging
- **Session Management**: Automatic session timeout and re-authentication
- **Environment Isolation**: Minimal environment variables for subprocess execution
- **Timeout Protection**: Configurable timeouts prevent hanging authentication

### Best Practices
- Never log, print, or store credentials
- Use secure temporary files for sensitive data processing
- Validate all input data before processing
- Sanitize all output data in logs and reports
- Follow principle of least privilege for file permissions

For detailed security guidelines, see [Security Documentation](docs/security.md).

## Configuration

### Configuration Hierarchy

The application supports multiple configuration sources with the following priority:

1. **Command-line arguments** (highest priority)
2. **Configuration files** (`~/.ticket-analyzer/config.json` or `config.ini`)
3. **Environment variables** (prefixed with `TICKET_ANALYZER_`)
4. **Default values** (lowest priority)

### Configuration File Examples

**JSON Format** (`config.json`):
```json
{
  "output": {
    "default_format": "table",
    "max_results": 1000,
    "sanitize_output": true
  },
  "authentication": {
    "timeout_seconds": 60,
    "max_retry_attempts": 3,
    "check_interval_seconds": 300
  },
  "logging": {
    "level": "INFO",
    "sanitize_logs": true
  }
}
```

**INI Format** (`config.ini`):
```ini
[output]
default_format = table
max_results = 1000
sanitize_output = true

[authentication]
timeout_seconds = 60
max_retry_attempts = 3
check_interval_seconds = 300

[logging]
level = INFO
sanitize_logs = true
```

### Environment Variables

```bash
export TICKET_ANALYZER_LOG_LEVEL=DEBUG
export TICKET_ANALYZER_MAX_RESULTS=500
export TICKET_ANALYZER_TIMEOUT=90
```

## Troubleshooting

### Common Issues

#### Authentication Problems

**Problem**: "Authentication failed" error
```bash
Error: Authentication failed. Please run 'mwinit' to authenticate.
```

**Solutions**:
1. Run `mwinit -o` to refresh authentication
2. Check network connectivity to Amazon internal systems
3. Verify Midway credentials are valid
4. Increase timeout in configuration if needed

#### Data Access Issues

**Problem**: "No tickets found" with valid search criteria
```bash
Warning: No tickets found matching the specified criteria.
```

**Solutions**:
1. Verify date ranges are correct (format: YYYY-MM-DD)
2. Check status filter values match system statuses
3. Ensure you have access to the specified resolver groups
4. Try broader search criteria to test connectivity

#### Performance Issues

**Problem**: Slow processing with large datasets
```bash
Processing... (this may take several minutes)
```

**Solutions**:
1. Reduce `--max-results` to limit dataset size
2. Use `--start-date` and `--end-date` to narrow time range
3. Filter by specific `--resolver-group` or `--assignee`
4. Use `--progress` flag to monitor processing status

#### Memory Issues

**Problem**: "Memory error" with very large datasets
```bash
MemoryError: Unable to allocate array
```

**Solutions**:
1. Reduce batch size in configuration
2. Process data in smaller date ranges
3. Use streaming processing for large datasets
4. Increase system memory or use a more powerful machine

### Getting Help

1. **Check the logs**: Use `--verbose` flag for detailed output
2. **Review configuration**: Ensure all settings are correct with `ticket-analyzer config show`
3. **Test connectivity**: Verify access to internal systems
4. **Check documentation**: Review relevant sections in [docs/](docs/)
5. **Contact support**: Create an issue with error details and logs (sanitized)

### Debug Mode

Enable debug mode for detailed troubleshooting:

```bash
# Enable debug logging
ticket-analyzer analyze --verbose --log-level DEBUG

# Save debug output to file
ticket-analyzer analyze --verbose 2> debug.log
```

## Performance

### Optimization Tips

- **Use date filters**: Limit analysis to specific time periods
- **Filter by resolver group**: Focus on specific teams or areas
- **Batch processing**: Process large datasets in smaller chunks
- **Output format**: Use JSON/CSV for large datasets instead of HTML
- **Progress monitoring**: Use `--progress` flag for long-running operations

### Performance Benchmarks

| Dataset Size | Processing Time | Memory Usage | Recommended Settings |
|--------------|----------------|--------------|---------------------|
| < 1,000 tickets | < 5 seconds | < 100 MB | Default settings |
| 1,000 - 10,000 | 5-30 seconds | 100-500 MB | `--max-results 5000` |
| 10,000 - 50,000 | 30-120 seconds | 500 MB - 2 GB | Date range filtering |
| > 50,000 | > 2 minutes | > 2 GB | Batch processing |

## FAQ

### General Questions

**Q: What ticket systems are supported?**
A: Currently supports Amazon's internal ticketing system (t.corp.amazon.com) via MCP integration.

**Q: Can I use this tool outside Amazon's network?**
A: No, this tool requires access to Amazon's internal network and Midway authentication.

**Q: What Python versions are supported?**
A: Python 3.7 and higher. The tool is specifically designed for Python 3.7 compatibility.

### Configuration Questions

**Q: Where should I put my configuration file?**
A: Place it at `~/.ticket-analyzer/config.json` or `~/.ticket-analyzer/config.ini` for user-specific settings.

**Q: Can I use environment variables for configuration?**
A: Yes, use the `TICKET_ANALYZER_` prefix (e.g., `TICKET_ANALYZER_LOG_LEVEL=DEBUG`).

### Security Questions

**Q: How is sensitive data handled?**
A: All data is automatically sanitized to remove PII, credentials are never logged, and temporary files use secure permissions.

**Q: Is my authentication information stored?**
A: No, the tool only checks authentication status and never stores credentials.

### Usage Questions

**Q: How do I analyze tickets for my team?**
A: Use `--resolver-group "Your Team Name"` to filter by your team's resolver group.

**Q: Can I generate reports for multiple time periods?**
A: Yes, use different `--start-date` and `--end-date` combinations, or run the tool multiple times with different parameters.

## Contributing

We welcome contributions! Please see our [Contributing Guide](docs/contributing.md) for details on:

- Code of conduct and community guidelines
- Development setup and workflow
- Testing requirements and standards
- Code review process
- Documentation standards

### Quick Contribution Steps

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following our coding standards
4. Add tests for new functionality
5. Run the test suite (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions:

- **Documentation**: Check the [docs/](docs/) directory for detailed guides
- **Issues**: Create an issue in the repository with detailed information
- **Security**: For security-related issues, follow responsible disclosure practices
- **Development**: Join our development discussions and code reviews

## Acknowledgments

- Amazon's Builder MCP team for the integration framework
- The Python community for excellent libraries (pandas, click, matplotlib)
- Contributors and maintainers who make this project possible

---

**Note**: This tool is designed for use within Amazon's internal network and requires appropriate access and authentication. Please ensure you have the necessary permissions before using this tool.