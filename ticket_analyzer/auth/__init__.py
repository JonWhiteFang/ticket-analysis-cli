"""Authentication module for secure Midway integration.

This module provides comprehensive authentication functionality including:
- Secure Midway authentication with subprocess isolation
- Session management with automatic expiry
- Authentication validation and error handling
- Secure memory management and credential protection
"""

from __future__ import annotations

from .midway_auth import MidwayAuthenticator, SecureMidwayAuthenticator
from .session import AuthenticationSession, SecureAuthenticationSession
from .auth_validator import AuthenticationValidator, SecureAuthenticationValidator

__all__ = [
    "MidwayAuthenticator",
    "SecureMidwayAuthenticator", 
    "AuthenticationSession",
    "SecureAuthenticationSession",
    "AuthenticationValidator",
    "SecureAuthenticationValidator"
]