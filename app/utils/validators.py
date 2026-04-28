"""
Input validation and sanitization utilities.
Protects against XSS and ensures data integrity.
"""

import re
import html as html_module


def sanitize_string(value: str, max_length: int = 500) -> str:
    """
    Sanitize a string input: strip, escape HTML, and truncate.

    Args:
        value: Raw string input.
        max_length: Maximum allowed length.

    Returns:
        Sanitized string.
    """
    if not value:
        return ''
    value = str(value).strip()
    value = html_module.escape(value)
    return value[:max_length]


def validate_email(email: str) -> bool:
    """Validate email format using a simple regex."""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def validate_date(date_str: str) -> bool:
    """Validate date string in YYYY-MM-DD format."""
    if not date_str:
        return False
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    return bool(re.match(pattern, date_str.strip()))


def validate_password(password: str, min_length: int = 6) -> tuple:
    """
    Validate password strength.

    Returns:
        (is_valid: bool, message: str)
    """
    if not password:
        return False, "Password is required."
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters."
    return True, "OK"


def validate_required_fields(fields: dict) -> tuple:
    """
    Check that all required fields are present and non-empty.

    Args:
        fields: Dict of { field_name: value }

    Returns:
        (is_valid: bool, missing_fields: list)
    """
    missing = [name for name, val in fields.items() if not val or not str(val).strip()]
    return len(missing) == 0, missing
