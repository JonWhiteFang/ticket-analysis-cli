---
inclusion: fileMatch
fileMatchPattern: '{requirements*.txt,pyproject.toml,setup.py,package.json}'
---

# Dependency Management

## Python 3.7 Compatible Dependencies

### Version Constraints
```txt
# requirements.txt
click>=7.0,<9.0
pandas>=1.0.0,<2.0.0
tqdm>=4.50.0,<5.0.0
typing-extensions>=3.7.4; python_version<"3.8"
dataclasses>=0.6; python_version<"3.7"
```

### Node.js 16 Compatibility
- MCP components must support Node.js 16+
- Use package.json engines field to enforce version
- Test with Node.js 16 LTS in CI/CD

### Virtual Environment Setup
```bash
# Create virtual environment
python3.7 -m venv venv
source venv/bin/activate  # On macOS/Linux
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Requirements Management
- Pin exact versions in requirements.txt for production
- Use requirements-dev.txt for development dependencies
- Regular dependency updates with security scanning
- Document breaking changes in CHANGELOG.md

### Security Considerations
- Use `pip-audit` for vulnerability scanning
- Pin dependencies to avoid supply chain attacks
- Review dependency licenses for compliance
- Use private PyPI for internal packages

### Development Dependencies
```txt
# requirements-dev.txt
pytest>=6.0.0,<8.0.0
pytest-cov>=2.10.0,<4.0.0
black>=21.0.0,<23.0.0
flake8>=3.8.0,<5.0.0
isort>=5.0.0,<6.0.0
mypy>=0.800,<1.0.0
```