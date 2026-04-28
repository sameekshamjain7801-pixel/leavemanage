"""
Admin credentials service.
Manages HOD/Principal credentials stored in a JSON file.
In production, consider migrating to a database table.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)

ADMIN_CREDS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'admin_creds.json')


def get_admin_creds() -> dict:
    """Load admin credentials from file, with fallback defaults."""
    if os.path.exists(ADMIN_CREDS_FILE):
        try:
            with open(ADMIN_CREDS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error("Error reading admin credentials: %s", e)

    # Default fallback
    from flask import current_app
    return dict(current_app.config.get('DEFAULT_ADMIN_CREDS', {
        'hod1': 'admin123',
        'hod2': 'admin123',
        'principal': 'admin123',
    }))


def save_admin_creds(creds: dict) -> bool:
    """Persist admin credentials to file."""
    try:
        with open(ADMIN_CREDS_FILE, 'w') as f:
            json.dump(creds, f, indent=2)
        logger.info("Admin credentials updated")
        return True
    except Exception as e:
        logger.error("Error saving admin credentials: %s", e)
        return False


def verify_admin_password(username: str, password: str) -> bool:
    """Verify an admin user's password."""
    creds = get_admin_creds()
    stored = creds.get(username)
    return stored is not None and stored == password


def update_admin_password(username: str, new_password: str) -> bool:
    """Update an admin user's password."""
    creds = get_admin_creds()
    if username not in creds:
        return False
    creds[username] = new_password
    return save_admin_creds(creds)
