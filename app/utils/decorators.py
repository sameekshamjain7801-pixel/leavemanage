"""
Authentication decorators for route protection.
"""

from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(f):
    """Ensure user is logged in."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'role' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Ensure user is an admin (HOD or Principal)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'role' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login'))
        if session['role'] not in ('hod1', 'hod2', 'principal'):
            flash("Access denied. Admin privileges required.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def faculty_required(f):
    """Ensure user is a faculty member."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'role' not in session or session['role'] != 'faculty':
            flash("Please log in as faculty to access this page.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def hod_required(f):
    """Ensure user is an HOD."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'role' not in session or session['role'] not in ('hod1', 'hod2'):
            flash("Access denied. HOD privileges required.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated
