# Examples Directory

This directory contains example configurations, scripts, and usage patterns for the Ticket Analysis CLI tool.

## Contents

- **Configuration Examples**: Sample configuration files for different use cases
- **Usage Scripts**: Automation scripts and common usage patterns
- **Integration Templates**: Templates for integrating with other tools and workflows
- **Development Setup**: Examples for development environment configuration

## Configuration Files

- `config.json.example` - JSON configuration with detailed comments
- `config.ini.example` - INI configuration with section explanations
- `config-minimal.json` - Minimal configuration for basic usage
- `config-advanced.json` - Advanced configuration with all options
- `config-team.json` - Team-specific configuration template

## Scripts

- `daily-analysis.sh` - Daily ticket analysis automation
- `team-report.sh` - Generate team performance reports
- `bulk-analysis.py` - Process multiple date ranges
- `integration-example.py` - Python integration example

## Integration Templates

- `jenkins-pipeline.groovy` - Jenkins CI/CD integration
- `github-actions.yml` - GitHub Actions workflow
- `cron-setup.sh` - Cron job setup for regular analysis

## Development

- `dev-config.json` - Development environment configuration
- `test-data-generator.py` - Generate test data for development
- `setup-dev-env.sh` - Development environment setup script

## Usage

Copy the relevant example files to your configuration directory and modify them according to your needs:

```bash
# Copy basic configuration
cp examples/config.json.example ~/.ticket-analyzer/config.json

# Copy automation script
cp examples/daily-analysis.sh ~/bin/
chmod +x ~/bin/daily-analysis.sh
```

For detailed explanations of each example, see the individual file comments and the main documentation.