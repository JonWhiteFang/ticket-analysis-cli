#!/usr/bin/env python3
"""Setup script for ticket-analyzer package."""

from setuptools import setup, find_packages

setup(
    name="ticket-analyzer",
    version="1.0.0",
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'ticket-analyzer=ticket_analyzer.cli.main:cli',
        ],
    },
    python_requires=">=3.7",
    install_requires=[
        "click>=7.0,<9.0",
        "pandas>=1.0.0,<2.0.0",
        "tqdm>=4.50.0,<5.0.0",
        "colorama>=0.4.3,<1.0.0",
        "jinja2>=2.11.0,<4.0.0",
        "matplotlib>=3.1.0,<4.0.0",
        "seaborn>=0.11.0,<1.0.0",
        "typing-extensions>=3.7.4; python_version<'3.8'",
        "dataclasses>=0.6; python_version<'3.7'",
        "cryptography>=3.0.0,<4.0.0",
        "pyyaml>=5.3.0,<7.0.0",
        "toml>=0.10.0,<1.0.0",
        "structlog>=20.1.0,<24.0.0",
        "requests>=2.25.0,<3.0.0",
        "urllib3>=1.26.0,<2.0.0",
        "python-dateutil>=2.8.0,<3.0.0",
        "numpy>=1.19.0,<2.0.0; python_version>='3.7'",
    ],
)