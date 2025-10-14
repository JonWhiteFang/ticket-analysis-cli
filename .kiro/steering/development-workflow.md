---
inclusion: manual
---

# Development Workflow

## Git Workflow and Branching Strategy

### Branch Naming Conventions
```bash
# Feature branches
feature/ticket-analysis-metrics
feature/mcp-integration
feature/cli-improvements

# Bug fix branches
bugfix/authentication-timeout
bugfix/data-sanitization-issue

# Hotfix branches (for production issues)
hotfix/security-vulnerability-fix
hotfix/critical-auth-bug

# Release branches
release/v1.0.0
release/v1.1.0
```

### Git Workflow Process
```bash
# 1. Start new feature from main
git checkout main
git pull origin main
git checkout -b feature/new-feature-name

# 2. Make changes with frequent commits
git add .
git commit -m "feat: add ticket metrics calculation

- Implement resolution time calculator
- Add status distribution analysis
- Include comprehensive test coverage

Closes #123"

# 3. Keep feature branch updated
git checkout main
git pull origin main
git checkout feature/new-feature-name
git rebase main

# 4. Push feature branch
git push origin feature/new-feature-name

# 5. Create pull request
# - Use PR template
# - Request code review
# - Ensure CI passes

# 6. Merge after approval
git checkout main
git pull origin main
git branch -d feature/new-feature-name
```

### Conventional Commits Format
```bash
# Commit message format
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]

# Types
feat:     # New feature
fix:      # Bug fix
docs:     # Documentation changes
style:    # Code style changes (formatting, etc.)
refactor: # Code refactoring
test:     # Adding or updating tests
chore:    # Maintenance tasks
perf:     # Performance improvements
ci:       # CI/CD changes
build:    # Build system changes

# Examples
feat(auth): add Midway authentication support

Implement secure authentication flow with:
- Session management
- Automatic re-authentication
- Timeout handling

Closes #45

fix(cli): resolve argument parsing issue

The --output flag was not properly handling file paths
with spaces. Updated argument parser to handle quoted paths.

Fixes #67

docs(readme): update installation instructions

Add Python 3.7 requirement and virtual environment setup
instructions for better onboarding experience.

test(models): add comprehensive ticket model tests

- Test ticket creation and validation
- Test resolution time calculations
- Add edge case coverage for date handling

chore(deps): update dependencies to latest versions

Update pandas to 1.5.3 and click to 8.1.0 for security
patches and performance improvements.
```

## Code Review Checklist

### Pre-Review Checklist (Author)
```markdown
## Before Requesting Review

- [ ] Code follows Python 3.7 compatibility requirements
- [ ] All tests pass locally
- [ ] Code coverage meets 80% minimum requirement
- [ ] No sensitive data in code or commit messages
- [ ] Documentation updated for new features
- [ ] Type hints added for all new functions
- [ ] Error handling implemented appropriately
- [ ] Logging added with proper sanitization
- [ ] Security considerations addressed
- [ ] Performance impact considered

## Code Quality Checks

- [ ] Functions are single-purpose and well-named
- [ ] Classes follow single responsibility principle
- [ ] No code duplication
- [ ] Complex logic is commented
- [ ] Magic numbers replaced with constants
- [ ] Imports organized correctly
- [ ] No unused imports or variables
```

### Review Checklist (Reviewer)
```markdown
## Code Review Checklist

### Functionality
- [ ] Code solves the intended problem
- [ ] Edge cases are handled
- [ ] Error conditions are properly managed
- [ ] Business logic is correct

### Security
- [ ] Input validation is comprehensive
- [ ] No sensitive data exposure
- [ ] Authentication/authorization properly implemented
- [ ] SQL injection prevention measures in place
- [ ] File operations use secure permissions

### Code Quality
- [ ] Code is readable and maintainable
- [ ] Follows established patterns and conventions
- [ ] Appropriate abstractions used
- [ ] No unnecessary complexity
- [ ] Performance considerations addressed

### Testing
- [ ] Adequate test coverage
- [ ] Tests are meaningful and comprehensive
- [ ] Mock usage is appropriate
- [ ] Integration tests cover key workflows

### Documentation
- [ ] Code is self-documenting
- [ ] Complex logic is explained
- [ ] API documentation is complete
- [ ] README updated if needed
```

## Continuous Integration Pipeline

### GitHub Actions Workflow
```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.7, 3.8, 3.9]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Lint with flake8
      run: |
        flake8 ticket_analyzer tests --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 ticket_analyzer tests --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics
    
    - name: Format check with black
      run: |
        black --check ticket_analyzer tests
    
    - name: Import sorting check with isort
      run: |
        isort --check-only ticket_analyzer tests
    
    - name: Type checking with mypy
      run: |
        mypy ticket_analyzer
    
    - name: Test with pytest
      run: |
        pytest --cov=ticket_analyzer --cov-report=xml --cov-report=term-missing
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        fail_ci_if_error: true

  security:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.7
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install bandit safety
    
    - name: Security check with bandit
      run: |
        bandit -r ticket_analyzer -f json -o bandit-report.json
    
    - name: Dependency vulnerability check
      run: |
        safety check --json --output safety-report.json
    
    - name: Upload security reports
      uses: actions/upload-artifact@v3
      with:
        name: security-reports
        path: |
          bandit-report.json
          safety-report.json
```

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: debug-statements

  - repo: https://github.com/psf/black
    rev: 22.12.0
    hooks:
      - id: black
        language_version: python3.7

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=88, --extend-ignore=E203,W503]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v0.991
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.4
    hooks:
      - id: bandit
        args: ["-c", "pyproject.toml"]
```

## Release Management and Versioning

### Semantic Versioning Strategy
```bash
# Version format: MAJOR.MINOR.PATCH
# Example: 1.2.3

# MAJOR version: incompatible API changes
# MINOR version: backwards-compatible functionality additions
# PATCH version: backwards-compatible bug fixes

# Pre-release versions
1.0.0-alpha.1    # Alpha release
1.0.0-beta.1     # Beta release
1.0.0-rc.1       # Release candidate
```

### Release Process
```bash
# 1. Create release branch
git checkout main
git pull origin main
git checkout -b release/v1.2.0

# 2. Update version numbers
# - Update __version__ in __init__.py
# - Update version in setup.py/pyproject.toml
# - Update CHANGELOG.md

# 3. Final testing
python -m pytest
python -m flake8 ticket_analyzer
python -m mypy ticket_analyzer

# 4. Commit version updates
git add .
git commit -m "chore(release): bump version to 1.2.0"

# 5. Create pull request for release
# - Review all changes since last release
# - Ensure documentation is updated
# - Verify CI passes

# 6. Merge to main and tag
git checkout main
git pull origin main
git tag -a v1.2.0 -m "Release version 1.2.0"
git push origin v1.2.0

# 7. Create GitHub release
# - Use tag v1.2.0
# - Include changelog
# - Attach distribution files if applicable
```

### Changelog Management
```markdown
# CHANGELOG.md

## [Unreleased]

### Added
- New ticket analysis metrics
- Enhanced error handling

### Changed
- Improved authentication flow
- Updated dependencies

### Fixed
- Resolved CLI argument parsing issue
- Fixed data sanitization bug

### Security
- Enhanced input validation
- Improved credential handling

## [1.1.0] - 2024-01-15

### Added
- MCP integration for ticket retrieval
- Comprehensive data sanitization
- CLI progress indicators

### Changed
- Refactored authentication system
- Improved error messages

### Fixed
- Authentication timeout issues
- Memory leak in data processing

## [1.0.0] - 2024-01-01

### Added
- Initial release
- Basic ticket analysis functionality
- CLI interface
- Authentication support
```

### Hotfix Process
```bash
# For critical production issues

# 1. Create hotfix branch from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-security-fix

# 2. Make minimal fix
# - Focus only on the critical issue
# - Avoid feature additions
# - Include tests for the fix

# 3. Test thoroughly
python -m pytest
# Run additional security tests if applicable

# 4. Fast-track review
# - Request immediate review
# - Focus on fix correctness
# - Verify no regressions

# 5. Deploy immediately after merge
git checkout main
git pull origin main
git tag -a v1.1.1 -m "Hotfix: critical security vulnerability"
git push origin v1.1.1

# 6. Backport to develop if needed
git checkout develop
git cherry-pick <hotfix-commit-hash>
git push origin develop
```