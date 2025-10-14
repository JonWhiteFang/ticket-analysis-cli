# CLI Reference Guide

## Overview

The Ticket Analysis CLI provides a comprehensive command-line interface for analyzing ticket data from Amazon's internal systems. The CLI is built with Click framework and follows modern CLI design principles with extensive validation, error handling, and user-friendly output.

## Table of Contents

1. [Global Options](#global-options)
2. [Analyze Command](#analyze-command)
3. [Config Command](#config-command)
4. [Report Command](#report-command)
5. [Environment Variables](#environment-variables)
6. [Exit Codes](#exit-codes)
7. [Examples](#examples)
8. [Troubleshooting](#troubleshooting)

## Global Options

These options are available for all commands:

```bash
ticket-analyzer [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS]
```

### Global Flags

| Option | Description | Default |
|--------|-------------|---------|
| `--version` | Show version information and exit | - |
| `--verbose, -v` | Enable verbose output with detailed logging | false |
| `--config, -c PATH` | Path to configuration file (JSON or INI format) | auto-detect |
| `--output-dir PATH` | Directory for output files | ./reports |
| `--help` | Show help message and exit | - |

### Examples

```bash
# Show version
ticket-analyzer --version

# Enable verbose logging for all commands
ticket-analyzer --verbose analyze --status Open

# Use custom configuration file
ticket-analyzer --config /path/to/config.json analyze

# Set custom output directory
ticket-analyzer --output-dir /tmp/reports analyze --format html
```

## Analyze Command

The primary command for analyzing ticket data with comprehensive filtering and reporting options.

### Syntax

```bash
ticket-analyzer analyze [OPTIONS]
```

### Time Period Options

Control the time range for ticket analysis:

| Option | Type | Description | Default | Example |
|--------|------|-------------|---------|---------|
| `--start-date` | DateTime | Start date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS) | 30 days ago | `--start-date 2024-01-01` |
| `--end-date` | DateTime | End date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS) | today | `--end-date 2024-01-31` |
| `--days-back` | Integer | Number of days back from today (1-365) | 30 | `--days-back 7` |
| `--date-range` | Choice | Predefined ranges: today, yesterday, week, month, quarter | none | `--date-range week` |

**Note**: You can only specify up to two time period options simultaneously.

### Filtering Options

Filter tickets based on various criteria:

| Option | Type | Description | Example |
|--------|------|-------------|---------|
| `--ticket-ids` | Multiple | Specific ticket IDs (supports T123456, ABC-123456, P123456, V1234567890 formats) | `--ticket-ids T123456 T789012` |
| `--status` | Multiple | Filter by ticket status | `--status Open "In Progress" Resolved` |
| `--severity` | Multiple | Filter by severity (SEV_1, SEV_2, SEV_3, SEV_4, SEV_5) | `--severity SEV_1 SEV_2` |
| `--assignee` | Multiple | Filter by assignee username | `--assignee user1 user2` |
| `--resolver-group` | Multiple | Filter by resolver group | `--resolver-group "Team A" "Team B"` |
| `--tags` | Multiple | Filter by tags | `--tags urgent production bug` |
| `--search-term` | String | Search in ticket title/description | `--search-term "authentication error"` |

### Analysis Options

Control what analysis is performed:

| Option | Type | Description | Default |
|--------|------|-------------|---------|
| `--include-resolved` | Flag | Include resolved tickets in analysis | false |
| `--exclude-automated` | Flag | Exclude automated tickets from analysis | false |
| `--priority-analysis` | Flag | Include priority-based analysis | false |
| `--trend-analysis` | Flag | Include trend analysis over time | false |
| `--team-performance` | Flag | Include team performance metrics | false |
| `--export-raw-data` | Flag | Export raw ticket data along with analysis | false |

### Output Options

Control output format and destination:

| Option | Type | Description | Default | Example |
|--------|------|-------------|---------|---------|
| `--format, -f` | Choice | Output format: table, json, csv, html | table | `--format json` |
| `--output, -o` | Path | Output file path | stdout | `--output report.html` |
| `--max-results` | Integer | Maximum results (1-10000) | 1000 | `--max-results 500` |
| `--include-charts` | Flag | Include charts in HTML reports | true | `--include-charts` |
| `--no-color` | Flag | Disable colored output | false | `--no-color` |

### Configuration Options

Override default configuration:

| Option | Type | Description | Default | Example |
|--------|------|-------------|---------|---------|
| `--config-file` | Path | Override configuration file path | auto-detect | `--config-file custom.json` |
| `--timeout` | Integer | Request timeout in seconds (10-300) | 60 | `--timeout 120` |
| `--batch-size` | Integer | Batch size for processing (10-1000) | 100 | `--batch-size 50` |

### Authentication Options

Control authentication behavior:

| Option | Type | Description | Default | Example |
|--------|------|-------------|---------|---------|
| `--auth-timeout` | Integer | Authentication timeout (30-300 seconds) | 60 | `--auth-timeout 90` |
| `--force-auth` | Flag | Force re-authentication | false | `--force-auth` |
| `--skip-auth-check` | Flag | Skip initial auth check (use with caution) | false | `--skip-auth-check` |

### Examples

```bash
# Basic analysis of open tickets from last week
ticket-analyzer analyze --status Open --date-range week

# Comprehensive team analysis with trends and charts
ticket-analyzer analyze \
  --resolver-group "My Team" \
  --trend-analysis \
  --team-performance \
  --format html \
  --output team-report.html

# High-priority ticket analysis with raw data export
ticket-analyzer analyze \
  --severity SEV_1 SEV_2 \
  --priority-analysis \
  --export-raw-data \
  --format json \
  --output priority-tickets.json

# Search for authentication issues in production
ticket-analyzer analyze \
  --search-term "authentication" \
  --tags production \
  --include-resolved \
  --days-back 90 \
  --verbose
```

## Config Command

Manage application configuration settings with support for JSON and INI formats.

### Syntax

```bash
ticket-analyzer config SUBCOMMAND [OPTIONS]
```

### Subcommands

#### show - Display Configuration

Display current configuration settings:

```bash
ticket-analyzer config show [OPTIONS]
```

| Option | Type | Description | Example |
|--------|------|-------------|---------|
| `--config-file` | Path | Specific configuration file to display | `--config-file custom.json` |
| `--section` | String | Show only specific section | `--section authentication` |
| `--format` | Choice | Output format: table, json, yaml | `--format json` |
| `--show-defaults` | Flag | Include default values | `--show-defaults` |
| `--show-sources` | Flag | Show value sources (file, env, default) | `--show-sources` |

#### set - Set Configuration Value

Set or update configuration values:

```bash
ticket-analyzer config set KEY VALUE [OPTIONS]
```

| Option | Type | Description | Example |
|--------|------|-------------|---------|
| `--config-file` | Path | Configuration file to update | `--config-file custom.json` |
| `--section` | String | Configuration section for the key | `--section authentication` |
| `--type` | Choice | Value type: string, int, float, bool, list | `--type int` |
| `--create-backup` | Flag | Create backup before modifying | `--create-backup` |

#### unset - Remove Configuration Value

Remove configuration values:

```bash
ticket-analyzer config unset KEY [OPTIONS]
```

| Option | Type | Description | Example |
|--------|------|-------------|---------|
| `--config-file` | Path | Configuration file to modify | `--config-file custom.json` |
| `--section` | String | Configuration section containing the key | `--section authentication` |
| `--create-backup` | Flag | Create backup before modifying | `--create-backup` |

#### validate - Validate Configuration

Validate configuration file format and values:

```bash
ticket-analyzer config validate [OPTIONS]
```

| Option | Type | Description | Example |
|--------|------|-------------|---------|
| `--config-file` | Path | Configuration file to validate | `--config-file custom.json` |
| `--strict` | Flag | Enable strict validation mode | `--strict` |
| `--fix-issues` | Flag | Attempt to fix issues automatically | `--fix-issues` |

#### init - Initialize Configuration

Create new configuration file:

```bash
ticket-analyzer config init [OPTIONS]
```

| Option | Type | Description | Default | Example |
|--------|------|-------------|---------|---------|
| `--config-file` | Path | Configuration file to create | auto-generate | `--config-file custom.json` |
| `--format` | Choice | File format: json, ini | json | `--format ini` |
| `--template` | Choice | Template: minimal, standard, comprehensive | standard | `--template comprehensive` |
| `--overwrite` | Flag | Overwrite existing file | false | `--overwrite` |

### Examples

```bash
# Show current configuration in JSON format
ticket-analyzer config show --format json --show-sources

# Set authentication timeout
ticket-analyzer config set authentication.timeout 120 --type int

# Set output format with section specification
ticket-analyzer config set output_format json --section output --type string

# Set list of default tags
ticket-analyzer config set default_tags "urgent,production,bug" --type list

# Remove custom setting
ticket-analyzer config unset custom_setting --section advanced

# Validate configuration and fix issues
ticket-analyzer config validate --strict --fix-issues

# Initialize comprehensive configuration
ticket-analyzer config init --format json --template comprehensive
```

## Report Command

Manage analysis reports including listing, conversion, merging, and cleanup.

### Syntax

```bash
ticket-analyzer report SUBCOMMAND [OPTIONS]
```

### Subcommands

#### list - List Reports

List available analysis reports:

```bash
ticket-analyzer report list [OPTIONS]
```

| Option | Type | Description | Default | Example |
|--------|------|-------------|---------|---------|
| `--directory, -d` | Path | Directory to list reports from | ./reports | `--directory /tmp/reports` |
| `--format-filter` | Choice | Filter by format: json, csv, html, all | all | `--format-filter html` |
| `--sort-by` | Choice | Sort by: name, date, size | date | `--sort-by size` |
| `--limit` | Integer | Maximum reports to show (1-100) | 20 | `--limit 10` |

#### convert - Convert Report Format

Convert reports between different formats:

```bash
ticket-analyzer report convert INPUT_FILE [OPTIONS]
```

| Option | Type | Description | Example |
|--------|------|-------------|---------|
| `--output, -o` | Path | Output file path | `--output converted.html` |
| `--format, -f` | Choice | Target format: json, csv, html | `--format html` |
| `--include-charts` | Flag | Include charts in HTML output | `--include-charts` |
| `--template` | String | Custom template for HTML output | `--template custom.html` |

#### merge - Merge Reports

Merge multiple reports into a single report:

```bash
ticket-analyzer report merge INPUT_FILES... [OPTIONS]
```

| Option | Type | Description | Default | Example |
|--------|------|-------------|---------|---------|
| `--output, -o` | Path | Output file for merged report | required | `--output combined.json` |
| `--format, -f` | Choice | Output format: json, csv, html | json | `--format html` |
| `--merge-strategy` | Choice | Strategy: combine, compare, aggregate | combine | `--merge-strategy aggregate` |

#### clean - Clean Old Reports

Remove old analysis reports:

```bash
ticket-analyzer report clean [OPTIONS]
```

| Option | Type | Description | Default | Example |
|--------|------|-------------|---------|---------|
| `--directory, -d` | Path | Directory to clean | ./reports | `--directory /tmp/reports` |
| `--older-than` | Integer | Remove reports older than N days | 30 | `--older-than 7` |
| `--format-filter` | Choice | Only clean specific formats | all | `--format-filter json` |
| `--dry-run` | Flag | Show what would be deleted | false | `--dry-run` |
| `--force` | Flag | Skip confirmation prompt | false | `--force` |

### Examples

```bash
# List HTML reports sorted by size
ticket-analyzer report list --format-filter html --sort-by size

# Convert JSON report to HTML with charts
ticket-analyzer report convert analysis.json --format html --include-charts

# Merge multiple reports with aggregation
ticket-analyzer report merge report1.json report2.json report3.json \
  --output quarterly-summary.html \
  --format html \
  --merge-strategy aggregate

# Clean reports older than 7 days (dry run first)
ticket-analyzer report clean --older-than 7 --dry-run
ticket-analyzer report clean --older-than 7 --force
```

## Environment Variables

The CLI supports environment variables with the `TICKET_ANALYZER_` prefix:

| Environment Variable | CLI Option | Description | Example |
|---------------------|------------|-------------|---------|
| `TICKET_ANALYZER_CONFIG_FILE` | `--config-file` | Default configuration file | `export TICKET_ANALYZER_CONFIG_FILE=/path/to/config.json` |
| `TICKET_ANALYZER_OUTPUT_FORMAT` | `--format` | Default output format | `export TICKET_ANALYZER_OUTPUT_FORMAT=json` |
| `TICKET_ANALYZER_OUTPUT_FILE` | `--output` | Default output file | `export TICKET_ANALYZER_OUTPUT_FILE=results.json` |
| `TICKET_ANALYZER_VERBOSE` | `--verbose` | Enable verbose mode | `export TICKET_ANALYZER_VERBOSE=true` |
| `TICKET_ANALYZER_MAX_RESULTS` | `--max-results` | Default maximum results | `export TICKET_ANALYZER_MAX_RESULTS=500` |
| `TICKET_ANALYZER_TIMEOUT` | `--timeout` | Default timeout | `export TICKET_ANALYZER_TIMEOUT=120` |
| `TICKET_ANALYZER_AUTH_TIMEOUT` | `--auth-timeout` | Authentication timeout | `export TICKET_ANALYZER_AUTH_TIMEOUT=90` |
| `TICKET_ANALYZER_FORCE_AUTH` | `--force-auth` | Force authentication | `export TICKET_ANALYZER_FORCE_AUTH=true` |
| `TICKET_ANALYZER_SKIP_AUTH_CHECK` | `--skip-auth-check` | Skip auth check | `export TICKET_ANALYZER_SKIP_AUTH_CHECK=true` |

### Setting Environment Variables

```bash
# Set default output format to JSON
export TICKET_ANALYZER_OUTPUT_FORMAT=json

# Set default configuration file
export TICKET_ANALYZER_CONFIG_FILE=~/.ticket-analyzer/config.json

# Enable verbose mode by default
export TICKET_ANALYZER_VERBOSE=true

# Set authentication timeout
export TICKET_ANALYZER_AUTH_TIMEOUT=120
```

## Exit Codes

The CLI uses standard exit codes to indicate different types of errors:

| Exit Code | Description | Common Causes |
|-----------|-------------|---------------|
| 0 | Success | Command completed successfully |
| 1 | Authentication Error | Invalid credentials, expired session, mwinit not run |
| 2 | Configuration Error | Invalid config file, missing required settings |
| 3 | Data Retrieval Error | Network issues, MCP connection problems, permission denied |
| 4 | Analysis Error | Invalid data, processing failures, insufficient data |
| 5 | General Error | Unexpected errors, programming bugs |
| 130 | Interrupted | User pressed Ctrl+C (SIGINT) |

### Handling Exit Codes in Scripts

```bash
#!/bin/bash

# Run analysis and handle different exit codes
ticket-analyzer analyze --status Open --format json --output results.json

case $? in
    0)
        echo "Analysis completed successfully"
        ;;
    1)
        echo "Authentication failed - run 'mwinit -o'"
        exit 1
        ;;
    2)
        echo "Configuration error - check config file"
        exit 1
        ;;
    3)
        echo "Data retrieval failed - check network and permissions"
        exit 1
        ;;
    4)
        echo "Analysis failed - check input data"
        exit 1
        ;;
    130)
        echo "Analysis interrupted by user"
        exit 130
        ;;
    *)
        echo "Unexpected error occurred"
        exit 1
        ;;
esac
```

## Examples

### Basic Usage Examples

```bash
# Quick analysis of recent open tickets
ticket-analyzer analyze --status Open --days-back 7

# Detailed team performance report
ticket-analyzer analyze \
  --resolver-group "My Team" \
  --team-performance \
  --trend-analysis \
  --format html \
  --output team-report.html

# Search for specific issues
ticket-analyzer analyze \
  --search-term "authentication error" \
  --tags production urgent \
  --include-resolved \
  --format json
```

### Advanced Usage Examples

```bash
# Comprehensive quarterly analysis with all metrics
ticket-analyzer analyze \
  --date-range quarter \
  --priority-analysis \
  --trend-analysis \
  --team-performance \
  --export-raw-data \
  --format html \
  --include-charts \
  --output quarterly-analysis.html \
  --verbose

# High-priority ticket analysis for multiple teams
ticket-analyzer analyze \
  --severity SEV_1 SEV_2 \
  --resolver-group "Team A" "Team B" "Team C" \
  --priority-analysis \
  --format json \
  --output priority-tickets.json \
  --max-results 5000

# Custom date range analysis with specific filters
ticket-analyzer analyze \
  --start-date "2024-01-01 00:00:00" \
  --end-date "2024-03-31 23:59:59" \
  --status Open Resolved \
  --exclude-automated \
  --tags production \
  --format csv \
  --output q1-production-tickets.csv
```

### Configuration Management Examples

```bash
# Set up initial configuration
ticket-analyzer config init --template comprehensive
ticket-analyzer config set authentication.timeout 120 --type int
ticket-analyzer config set output.default_format json --type string
ticket-analyzer config set output.max_results 2000 --type int

# Validate and fix configuration
ticket-analyzer config validate --strict --fix-issues

# Show configuration with sources
ticket-analyzer config show --format json --show-sources
```

### Report Management Examples

```bash
# Generate and manage reports
ticket-analyzer analyze --format json --output daily-report.json
ticket-analyzer report convert daily-report.json --format html --include-charts
ticket-analyzer report list --format-filter html --sort-by date

# Merge weekly reports into monthly summary
ticket-analyzer report merge week1.json week2.json week3.json week4.json \
  --output monthly-summary.html \
  --format html \
  --merge-strategy aggregate

# Clean up old reports
ticket-analyzer report clean --older-than 30 --dry-run
ticket-analyzer report clean --older-than 30 --force
```

## Troubleshooting

### Common Issues and Solutions

#### Authentication Problems

```bash
# Problem: "Authentication failed" error
# Solution: Refresh Midway authentication
mwinit -o
ticket-analyzer analyze --force-auth

# Problem: Authentication timeout
# Solution: Increase timeout
ticket-analyzer analyze --auth-timeout 120
```

#### Configuration Issues

```bash
# Problem: "Configuration file not found"
# Solution: Initialize configuration
ticket-analyzer config init

# Problem: "Invalid configuration"
# Solution: Validate and fix
ticket-analyzer config validate --strict --fix-issues
```

#### Data Retrieval Problems

```bash
# Problem: "No tickets found"
# Solution: Check filters and date ranges
ticket-analyzer analyze --verbose --days-back 90

# Problem: "Connection timeout"
# Solution: Increase timeout and reduce batch size
ticket-analyzer analyze --timeout 180 --batch-size 50
```

#### Performance Issues

```bash
# Problem: Slow processing
# Solution: Reduce data size and enable progress
ticket-analyzer analyze \
  --max-results 1000 \
  --batch-size 50 \
  --days-back 30 \
  --verbose

# Problem: Memory errors
# Solution: Use smaller batches and exclude raw data
ticket-analyzer analyze \
  --batch-size 25 \
  --max-results 500 \
  --format json
```

### Debug Mode

Enable comprehensive debugging:

```bash
# Enable verbose output with debug logging
ticket-analyzer --verbose analyze --status Open 2>&1 | tee debug.log

# Check configuration and environment
ticket-analyzer config show --show-sources --verbose
env | grep TICKET_ANALYZER
```

### Getting Help

```bash
# Show general help
ticket-analyzer --help

# Show command-specific help
ticket-analyzer analyze --help
ticket-analyzer config --help
ticket-analyzer report --help

# Show subcommand help
ticket-analyzer config show --help
ticket-analyzer report convert --help
```