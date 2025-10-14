# Steering Files Configuration

This directory contains concise steering files that provide context-specific guidance for development. Each file is configured with conditional inclusion patterns to ensure they're only loaded when relevant.

## Inclusion Patterns

### File Match Patterns
These files are automatically included when working with matching files:

- **testing-standards.md**: Test files (`test*`)
- **authentication-security.md**: Authentication files (`*auth*`)
- **cli-development-standards.md**: CLI files (`*cli*`)
- **data-sanitization.md**: Sanitization files (`*sanitiz*`)
- **mcp-integration-architecture.md**: MCP files (`*mcp*`)
- **documentation-standards.md**: Documentation files (`*{README,CHANGELOG,*.md}`)
- **dependency-management.md**: Dependency files (`{requirements*.txt,pyproject.toml,setup.py,package.json}`)
- **design-patterns.md**: Pattern files (`*{service,repository,pattern}*`)
- **clean-architecture-patterns.md**: Architecture files (`*{service,repository,model,domain}*`)
- **python-coding-standards.md**: Python files (`*.py`)
- **secure-coding-practices.md**: Security files (`*{security,secure,auth,valid}*`)

### Manual Inclusion
- **development-workflow.md**: Use `#development-workflow` for Git workflow and CI/CD guidance

## Recent Updates

All steering files have been made more concise while maintaining essential guidance:
- Removed verbose examples and repetitive content
- Focused on core patterns and best practices
- Kept practical code examples that demonstrate key concepts
- Maintained security and compatibility requirements

## Usage

Files are automatically included based on your current work context. For manual files, use `#filename` syntax in chat.