# Steering Documents for Ticket Analysis CLI Project

This document outlines the recommended steering documents that would be useful for maintaining code quality, architectural consistency, and security standards throughout the development of the ticket analysis CLI application.

## Coding Standards

### `python-coding-standards.md`
- Python 3.7 compatibility requirements and syntax constraints
- Type hinting standards using Python 3.7 compatible typing module
- Dataclass usage patterns with `@dataclass` decorator
- Import statement organization and `from __future__ import annotations`
- Error handling patterns and custom exception hierarchy
- Logging standards with structured logging and sanitization
- Code formatting with Black and linting with flake8/pylint

### `dependency-management.md`
- Python 3.7 compatible dependency version constraints
- Node.js 16 compatibility requirements for MCP components
- Virtual environment setup and management
- Requirements.txt maintenance and version pinning
- Security considerations for third-party dependencies

### `cli-development-standards.md`
- Click framework usage patterns and best practices
- Command-line argument design and validation
- Color-coded output standards (red=errors, green=success, blue=info)
- Progress indicator implementation with tqdm
- Signal handling and graceful shutdown procedures

## Architecture

### `clean-architecture-patterns.md`
- Layered architecture implementation (CLI → Application → Service → Infrastructure)
- Dependency injection patterns for testability
- Interface-based design with abstract base classes
- Single responsibility principle enforcement
- Separation of concerns between modules

### `design-patterns.md`
- Repository pattern for data access (MCPTicketRetriever)
- Strategy pattern for analysis types (metrics calculators)
- Template method pattern for reporting formats
- Chain of responsibility for configuration hierarchy
- Circuit breaker pattern for external service resilience

### `mcp-integration-architecture.md`
- Builder MCP integration patterns and best practices
- Node.js subprocess communication standards
- Error handling and retry logic for MCP calls
- Authentication flow with MCP services
- Data serialization and validation patterns

## Testing

### `testing-standards.md`
- Pytest framework usage and test organization
- Mock patterns for external dependencies (MCP, subprocess calls)
- Test coverage requirements (80% minimum for core modules)
- Unit test vs integration test boundaries
- Test data management and fixtures

### `test-driven-development.md`
- TDD workflow for new features
- Test naming conventions and organization
- Assertion patterns and error testing
- Performance testing for data processing
- CLI testing strategies with Click testing utilities

### `mocking-strategies.md`
- Subprocess mocking for authentication (mwinit)
- MCP service mocking patterns
- Pandas DataFrame testing with sample data
- File system mocking for configuration tests
- Network request mocking for API calls

## Security

### `authentication-security.md`
- Midway authentication best practices
- Subprocess security for mwinit calls
- Credential isolation and never logging sensitive data
- Session management and automatic re-authentication
- Authentication timeout handling

### `data-sanitization.md`
- Ticket data sanitization in logs and outputs
- PII detection and removal patterns
- Secure temporary file handling
- Error message sanitization to prevent information leakage
- Input validation and SQL injection prevention

### `secure-coding-practices.md`
- Input validation patterns for all user inputs
- Secure file operations and permissions
- Environment variable handling for sensitive configuration
- Subprocess execution security best practices
- Memory management for sensitive data

## Project Management

### `development-workflow.md`
- Git workflow and branching strategy
- Conventional commits format requirements
- Code review checklist and approval process
- Continuous integration pipeline requirements
- Release management and versioning strategy

### `documentation-standards.md`
- README structure and content requirements
- API documentation with docstring standards
- Configuration file documentation and examples
- User guide and troubleshooting documentation
- Architecture decision records (ADRs)

### `performance-monitoring.md`
- Performance benchmarking for data processing
- Memory usage monitoring and optimization
- API rate limiting and backoff strategies
- Logging performance impact considerations
- Resource cleanup and garbage collection patterns

## Implementation Notes

These steering documents would provide comprehensive guidance for:

1. **Code Quality**: Ensuring consistent coding standards across all modules
2. **Architecture**: Maintaining clean separation of concerns and design patterns
3. **Security**: Protecting sensitive data and implementing secure authentication
4. **Testing**: Achieving comprehensive test coverage with proper mocking strategies
5. **Project Management**: Following consistent development workflows and documentation

Each document should include specific examples, code snippets, and implementation patterns relevant to the ticket analysis CLI project's requirements, particularly focusing on Python 3.7 compatibility and Amazon's internal tooling integration.