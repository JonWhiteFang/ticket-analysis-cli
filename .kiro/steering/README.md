# Steering Files Configuration

This directory contains steering files that provide context-specific guidance for development. Each file is configured with conditional inclusion patterns to ensure they're only loaded when relevant.

## Inclusion Patterns

### File Match Patterns
These files are included when working with files that match specific patterns:

- **testing-standards.md**: Included when working with test files (`test*`)
- **authentication-security.md**: Included when working with authentication-related files (`*auth*`)
- **cli-development-standards.md**: Included when working with CLI-related files (`*cli*`)
- **data-sanitization.md**: Included when working with sanitization-related files (`*sanitiz*`)
- **mcp-integration-architecture.md**: Included when working with MCP-related files (`*mcp*`)
- **documentation-standards.md**: Included when working with documentation files (`*{README,CHANGELOG,*.md}`)
- **dependency-management.md**: Included when working with dependency files (`{requirements*.txt,pyproject.toml,setup.py,package.json}`)
- **design-patterns.md**: Included when working with service/repository/pattern files (`*{service,repository,pattern}*`)
- **clean-architecture-patterns.md**: Included when working with architecture files (`*{service,repository,model,domain}*`)
- **python-coding-standards.md**: Included when working with Python files (`*.py`)
- **secure-coding-practices.md**: Included when working with security-related files (`*{security,secure,auth,valid}*`)

### Manual Inclusion
These files are only included when explicitly referenced:

- **development-workflow.md**: Use `#development-workflow` to include Git workflow and CI/CD guidance

## Usage

The steering files will automatically be included based on the files you're working with. For manual inclusion files, reference them in your chat using the `#` syntax.

Example:
```
Help me set up a new feature branch #development-workflow
```

This ensures you get relevant guidance without overwhelming context from unrelated standards.