---
inclusion: fileMatch
fileMatchPattern: '{requirements*.txt,pyproject.toml,setup.py,package.json}'
---

# Dependency Management

## Python 3.7 Compatibility
```txt
# requirements.txt
click>=7.0,<9.0
pandas>=1.0.0,<2.0.0
tqdm>=4.50.0,<5.0.0
typing-extensions>=3.7.4; python_version<"3.8"
```

## Virtual Environment
```bash
python3.7 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Development Dependencies
```txt
# requirements-dev.txt
pytest>=6.0.0,<8.0.0
pytest-cov>=2.10.0,<4.0.0
black>=21.0.0,<23.0.0
flake8>=3.8.0,<5.0.0
mypy>=0.800,<1.0.0
```

## Security Best Practices
- Use `pip-audit` for vulnerability scanning
- Pin exact versions for production
- Regular dependency updates
- Review licenses for compliance