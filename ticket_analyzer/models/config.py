"""Configuration-related data models."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class ReportConfig:
    """Configuration for report generation."""
    format: str = "table"  # 'table', 'json', 'csv', 'html'
    output_path: Optional[str] = None
    include_charts: bool = True
    color_output: bool = True
    template_name: Optional[str] = None
    sanitize_output: bool = True
    max_results_display: int = 100


@dataclass
class AuthConfig:
    """Configuration for authentication settings."""
    timeout_seconds: int = 60
    max_retry_attempts: int = 3
    check_interval_seconds: int = 300  # 5 minutes
    session_duration_hours: int = 8