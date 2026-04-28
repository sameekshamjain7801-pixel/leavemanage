"""
Application configuration module.
Loads settings from environment variables with sensible defaults.
Supports Development and Production profiles.
"""

import os
from dotenv import load_dotenv

# Load .env file for local development
load_dotenv()


class BaseConfig:
    """Base configuration shared across all environments."""

    # Flask core
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-production')

    # Session
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour

    # Supabase
    SUPABASE_PROJECT_URL = os.environ.get(
        'SUPABASE_PROJECT_URL',
        'https://mygsvmoguhettdjwvkfn.supabase.co'
    )
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
    SUPABASE_LEAVE_TABLE = 'leave_requests'
    SUPABASE_FACULTY_TABLE = 'faculty_credentials'

    # Derived Supabase REST endpoints
    @property
    def SUPABASE_LEAVE_URL(self):
        return f"{self.SUPABASE_PROJECT_URL}/rest/v1/{self.SUPABASE_LEAVE_TABLE}"

    @property
    def SUPABASE_FACULTY_URL(self):
        return f"{self.SUPABASE_PROJECT_URL}/rest/v1/{self.SUPABASE_FACULTY_TABLE}"

    # SMTP / Email
    SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 465))
    SMTP_EMAIL = os.environ.get('SMTP_EMAIL', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    SMTP_SENDER_NAME = os.environ.get('SMTP_SENDER_NAME', 'LeaveFlow Administration')

    # Admin default credentials (overridden by env vars in production)
    DEFAULT_ADMIN_CREDS = {
        'hod1': os.environ.get('HOD1_PASSWORD', 'admin123'),
        'hod2': os.environ.get('HOD2_PASSWORD', 'admin123'),
        'principal': os.environ.get('PRINCIPAL_PASSWORD', 'admin123'),
    }

    # Application URL (used in emails)
    APP_URL = os.environ.get('APP_URL', 'http://127.0.0.1:5000')

    # Default leave quota
    DEFAULT_LEAVE_QUOTA = int(os.environ.get('DEFAULT_LEAVE_QUOTA', 20))


class DevelopmentConfig(BaseConfig):
    """Development-specific settings."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    TESTING = False


class ProductionConfig(BaseConfig):
    """Production-specific settings for Render deployment."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    TESTING = False

    # Enforce a real secret key in production
    @property
    def SECRET_KEY(self):
        key = os.environ.get('SECRET_KEY')
        if not key or key == 'change-me-in-production':
            raise ValueError(
                "SECRET_KEY environment variable must be set in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return key


# Map of environment names to config classes
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
}


def get_config():
    """Return the config object based on FLASK_ENV environment variable."""
    env = os.environ.get('FLASK_ENV', 'development').lower()
    return config_map.get(env, DevelopmentConfig)()
