# Contributing Guidelines

## Overview

We welcome contributions to the Ticket Analysis CLI tool! This document provides guidelines for contributing code, reporting issues, and participating in the development process.

## Getting Started

### Prerequisites

Before contributing, ensure you have:

- Python 3.7 or higher installed
- Node.js 16 or higher (for MCP components)
- Git configured with your name and email
- Access to Amazon's internal development environment

### Development Setup

1. **Fork and Clone**:
   ```bash
   git clone https://github.com/your-username/ticket-analyzer.git
   cd ticket-analyzer
   ```

2. **Set Up Development Environment**:
   ```bash
   # Run the development setup script
   ./scripts/dev-setup.sh
   
   # Or manually:
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements-dev.txt
   pip install -e .
   pre-commit install
   ```

3. **Verify Setup**:
   ```bash
   # Run tests to ensure everything works
   pytest
   
   # Run linting
   make lint
   
   # Test CLI
   ticket-analyzer --version
   ```

## Contribution Process

### 1. Issue Creation

Before starting work, create or find an existing issue:

- **Bug Reports**: Use the bug report template
- **Feature Requests**: Use the feature request template
- **Security Issues**: Report privately to the security team

#### Bug Report Template

```markdown
**Bug Description**
A clear description of the bug.

**Steps to Reproduce**
1. Run command: `ticket-analyzer analyze --status Open`
2. Observe error message
3. Check logs

**Expected Behavior**
What should have happened.

**Actual Behavior**
What actually happened.

**Environment**
- OS: macOS 12.0
- Python: 3.7.9
- Version: 1.0.0

**Additional Context**
Any other relevant information.
```

#### Feature Request Template

```markdown
**Feature Description**
Clear description of the proposed feature.

**Use Case**
Why is this feature needed? What problem does it solve?

**Proposed Solution**
How should this feature work?

**Alternatives Considered**
Other approaches you've considered.

**Additional Context**
Any other relevant information.
```

### 2. Development Workflow

1. **Create Feature Branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**:
   - Follow coding standards (see Development Guide)
   - Write tests for new functionality
   - Update documentation as needed

3. **Test Changes**:
   ```bash
   # Run all tests
   pytest
   
   # Run specific test categories
   pytest -m unit
   pytest -m integration
   
   # Check coverage
   pytest --cov=ticket_analyzer --cov-report=term-missing
   ```

4. **Commit Changes**:
   ```bash
   # Stage changes
   git add .
   
   # Commit with conventional format
   git commit -m "feat(auth): add session timeout configuration
   
   - Add configurable session timeout
   - Implement automatic session renewal
   - Add timeout validation
   
   Closes #123"
   ```

5. **Push and Create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```

### 3. Pull Request Guidelines

#### PR Title Format

Use conventional commit format:
- `feat: add new feature`
- `fix: resolve bug in authentication`
- `docs: update API documentation`
- `test: add unit tests for models`
- `refactor: improve error handling`

#### PR Description Template

```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed
- [ ] All tests pass

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No new warnings introduced
- [ ] Security considerations addressed

## Related Issues
Closes #123
Relates to #456

## Screenshots (if applicable)
Add screenshots for UI changes.
```

## Code Review Process

### Review Criteria

Reviewers will check for:

1. **Functionality**: Does the code work as intended?
2. **Code Quality**: Is the code clean, readable, and maintainable?
3. **Testing**: Are there adequate tests with good coverage?
4. **Security**: Are security best practices followed?
5. **Performance**: Are there any performance implications?
6. **Documentation**: Is documentation updated appropriately?

### Review Checklist

#### For Authors

- [ ] Code is self-documenting with clear variable/function names
- [ ] Complex logic is commented
- [ ] Error handling is comprehensive
- [ ] Security considerations are addressed
- [ ] Performance impact is considered
- [ ] Tests cover new functionality
- [ ] Documentation is updated
- [ ] Breaking changes are documented

#### For Reviewers

- [ ] Code logic is correct and efficient
- [ ] Error handling is appropriate
- [ ] Security vulnerabilities are not introduced
- [ ] Tests are comprehensive and meaningful
- [ ] Code follows project conventions
- [ ] Documentation is accurate and complete
- [ ] Performance implications are acceptable

### Review Process

1. **Automated Checks**: CI pipeline runs automatically
2. **Peer Review**: At least one team member reviews
3. **Security Review**: Required for security-related changes
4. **Approval**: All checks pass and reviewers approve
5. **Merge**: Squash and merge to main branch

## Coding Standards

### Python Style Guide

Follow PEP 8 with these specific guidelines:

- **Line Length**: 88 characters (Black default)
- **Imports**: Use isort with Black profile
- **Type Hints**: Required for all public functions
- **Docstrings**: Google style for all public functions/classes
- **Error Handling**: Use custom exception hierarchy

### Documentation Standards

- **Code Comments**: Explain why, not what
- **Docstrings**: Include examples for complex functions
- **API Documentation**: Update for all public interface changes
- **README**: Keep installation and usage instructions current

### Testing Standards

- **Coverage**: Minimum 80% for new code
- **Test Types**: Unit, integration, and security tests
- **Test Data**: Use factories, avoid hardcoded values
- **Mocking**: Mock external dependencies appropriately

## Security Guidelines

### Security Requirements

- **Input Validation**: Validate all user inputs
- **Data Sanitization**: Remove PII from logs and outputs
- **Authentication**: Use secure authentication methods
- **Dependencies**: Keep dependencies updated
- **Secrets**: Never commit secrets or credentials

### Security Review Process

Security-related changes require additional review:

1. **Security Team Review**: For authentication, authorization, or data handling changes
2. **Penetration Testing**: For significant security features
3. **Compliance Check**: Ensure compliance with internal security policies

## Release Process

### Version Management

We use Semantic Versioning (SemVer):

- **MAJOR**: Incompatible API changes
- **MINOR**: Backwards-compatible functionality additions
- **PATCH**: Backwards-compatible bug fixes

### Release Workflow

1. **Feature Freeze**: No new features for release branch
2. **Testing**: Comprehensive testing of release candidate
3. **Documentation**: Update changelog and documentation
4. **Release**: Tag and publish release
5. **Post-Release**: Monitor for issues and hotfixes

## Community Guidelines

### Code of Conduct

We are committed to providing a welcoming and inclusive environment:

- **Be Respectful**: Treat all contributors with respect
- **Be Collaborative**: Work together constructively
- **Be Inclusive**: Welcome diverse perspectives
- **Be Professional**: Maintain professional communication

### Communication Channels

- **Issues**: For bug reports and feature requests
- **Pull Requests**: For code discussions
- **Email**: For security issues or private matters
- **Team Chat**: For quick questions and discussions

## Getting Help

### Resources

- **Documentation**: Check docs/ directory
- **Examples**: See examples/ directory
- **Tests**: Look at test files for usage examples
- **Issues**: Search existing issues for similar problems

### Support Channels

1. **Documentation**: Start with project documentation
2. **Issues**: Search and create GitHub issues
3. **Team Contact**: Reach out to maintainers
4. **Internal Resources**: Use internal Amazon resources for environment-specific issues

## Recognition

We appreciate all contributions! Contributors will be:

- **Acknowledged**: In release notes and documentation
- **Credited**: In the contributors list
- **Invited**: To participate in project decisions

Thank you for contributing to the Ticket Analysis CLI tool!