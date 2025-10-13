# Ticket Analysis Application Recreation Prompt

Please create a ticket analysis CLI application with the following specifications:

## Technology Requirements
- **Node.js**: Version 16 (for any JavaScript components)
- **Python**: Version 3.7 compatibility (use `python3` command throughout)
- **Target Platform**: Linux with bash shell

## Project Overview
Create a Python CLI application for analyzing Amazon's internal ticketing system (t.corp.amazon.com) that generates metrics, trends, and HTML reports with visualizations.

## Core Architecture
```
auth/              # Midway authentication handlers
data_retrieval/    # API communication & error handling  
analysis/          # Metrics calculation & ticket analysis
reporting/         # CLI and HTML report generation
config/            # Configuration management
models.py          # @dataclass models + custom exceptions
interfaces.py      # Abstract base classes for all modules
main.py           # CLI entry point with Click framework
```

## Key Features Required

### 1. Authentication System
- Midway authentication via subprocess calls to `mwinit`
- Never log, print, or store credentials
- Validate authentication before API calls

### 2. Data Retrieval
- Integration with Amazon's Builder MCP (Model Context Protocol)
- Support for TicketingReadActions and TicketingWriteActions
- Full Lucene query syntax support
- Exponential backoff with jitter for rate limiting
- Handle empty datasets and malformed responses

### 3. Analysis Engine
- Use pandas DataFrames for data manipulation
- Calculate metrics and trends from ticket data
- Support date range analysis (default 30 days)
- Handle edge cases gracefully

### 4. Reporting System
- CLI reports with tabular format and color coding (colorama)
- HTML reports using Jinja2 templates with embedded CSS/JS
- Include matplotlib charts as base64 in HTML
- Progress indicators using tqdm

### 5. CLI Interface
- Built with Click framework
- Argument groups: Time Period, Output Options, Configuration, Authentication
- Default output directory: `./reports/`
- Graceful Ctrl+C handling with cleanup
- Color-coded output (red=errors, green=success, blue=info)

## Required Dependencies
```
requests>=2.25.0    # API communication
pandas>=1.3.0       # Data analysis (Python 3.7 compatible)
matplotlib>=3.3.0   # Visualization
seaborn>=0.11.0     # Statistical plots
jinja2>=3.0.0       # HTML templating
click>=8.0.0        # CLI framework
tqdm>=4.60.0        # Progress bars
colorama>=0.4.0     # Terminal colors
pytest>=6.0.0       # Testing framework
```

## Configuration System
Support configuration hierarchy (in priority order):
1. Command-line arguments
2. Configuration files (config.json, config.ini)
3. Environment variables
4. Default values

## Code Standards
- All data models use `@dataclass` with complete type hints
- Custom exceptions in `models.py` (ConfigurationError, AuthenticationError, etc.)
- All modules implement interfaces from `interfaces.py`
- Dependency injection pattern for testability
- Single responsibility principle

## Security Requirements
- Authentication only via subprocess calls to `mwinit`
- Sanitize all ticket data in logs and outputs
- Validate all input data before processing
- Use secure temporary files for sensitive data

## Testing Requirements
- Use pytest framework (`python3 -m pytest`)
- Mock all external dependencies
- Test success and failure scenarios
- Minimum 80% code coverage for core modules
- Integration tests for CLI commands

## File Structure to Create
```
├── auth/
│   ├── __init__.py
│   ├── midway_auth.py
│   └── test_midway_auth.py
├── data_retrieval/
│   ├── __init__.py
│   ├── mcp_ticket_retriever.py
│   └── test_mcp_ticket_retriever.py
├── analysis/
│   ├── __init__.py
│   ├── ticket_analyzer.py
│   └── test_ticket_analyzer.py
├── reporting/
│   ├── __init__.py
│   ├── cli_reporter.py
│   ├── html_reporter.py
│   ├── templates/
│   ├── test_cli_reporter.py
│   └── test_html_reporter.py
├── config/
│   ├── __init__.py
│   ├── config_manager.py
│   └── test_config_manager.py
├── logs/
├── reports/
├── models.py
├── interfaces.py
├── main.py
├── requirements.txt
├── pyproject.toml
├── config.json.example
├── config.ini.example
└── README.md
```

## MCP Integration Requirements
- Configure Builder MCP server for Amazon internal tooling
- Implement TicketingReadActions for ticket search and retrieval
- Support TaskeiGetTask and TaskeiListTasks for task management
- Include InternalSearch for documentation lookup
- Implement proper error handling and retry logic for MCP calls

## Development Workflow
1. Always use `python3` command (never `python`)
2. Run `python3 main.py --help` to verify functionality
3. Run `python3 -m pytest` after changes (all tests must pass)
4. Follow Conventional Commits format
5. Test main CLI functionality before committing

## CLI Usage Examples
```bash
# Basic usage
python3 main.py --days 30 --output ./reports/

# Debug mode
python3 main.py --days 7 --debug --format html

# Specific resolver group
python3 main.py --group "IT Support" --days 14
```

Please implement this application following Python 3.7 compatibility requirements and the architectural patterns described above. Focus on creating a minimal but complete implementation that can be extended later.