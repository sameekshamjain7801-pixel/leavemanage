"""
Authentication routes blueprint.
Handles login, logout, forgot password, and password changes.
"""

import logging
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from app.services.db_service import get_faculty_by_id, update_faculty, get_faculty_by_email
from app.services.admin_service import get_admin_creds, save_admin_creds, verify_admin_password
from app.utils.email_service import send_password_recovery_email
from app.utils.decorators import login_required
from app.utils.validators import sanitize_string

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/clear_notifications', methods=['POST'])
@login_required
def clear_notifications():
    """Dismiss all current notifications by storing their IDs in session."""
    dismissed = session.get('dismissed_notification_ids', [])
    current = session.get('current_notification_ids', [])
    session['dismissed_notification_ids'] = list(set(dismissed + current))
    # Return JSON for AJAX or redirect
    from flask import jsonify
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'ok': True})
    return redirect(request.referrer or url_for('dashboard.dashboard'))


@auth_bp.route('/')
def index():
    """Render landing page, or redirect if already logged in."""
    if 'role' in session:
        return _redirect_to_user_dashboard()
    return render_template('index.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login for both faculty and admin users."""
    if request.method == 'POST':
        username = sanitize_string(request.form.get('username', '')).lower()
        password = request.form.get('password', '')
        role_type = request.form.get('role_type', 'admin')

        if not username or not password:
            flash("Username and password are required.", "danger")
            return render_template('login.html')

        # ── Faculty Login ──
        if role_type == 'faculty':
            faculty = get_faculty_by_id(username)
            if not faculty:
                faculty = get_faculty_by_email(username)

            if faculty and faculty.get('password') == password:
                session['role'] = 'faculty'
                session['faculty_id'] = username
                session['faculty_name'] = faculty['name']
                session['faculty_email'] = faculty['email']
                session['faculty_department'] = faculty['department']
                session.permanent = True
                logger.info("Faculty login: %s", username)
                flash(f"Logged in successfully as {faculty['name']}", "success")
                return redirect(url_for('faculty.faculty_dashboard'))

            logger.warning("Failed faculty login attempt: %s", username)
            flash("Invalid Faculty ID or password. Please try again.", "danger")

        # ── Admin Login (HOD/Principal) ──
        else:
            # Accept both 'principal' and 'principle' spellings
            if username in ('principal', 'principle'):
                username = 'principal'

            if verify_admin_password(username, password):
                session['role'] = username
                session.permanent = True
                logger.info("Admin login: %s", username)
                flash(f"Logged in successfully as {username.upper()}", "success")
                return redirect(url_for('dashboard.dashboard'))

            logger.warning("Failed admin login attempt: %s", username)
            flash("Invalid username or password. Please try again.", "danger")

    # If already logged in, go to dashboard
    if request.method == 'GET' and 'role' in session:
        return _redirect_to_user_dashboard()

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """Clear session and redirect to login."""
    role = session.get('role', 'unknown')
    session.clear()
    logger.info("User logged out: %s", role)
    flash("You have been logged out.", "info")
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot_password', methods=['GET'])
def forgot_password():
    """Render the standalone forgot password page."""
    return render_template('forgot_password.html')


@auth_bp.route('/forgot_password', methods=['POST'])
def process_forgot_password():
    """Handle password recovery requests from the standalone page."""
    faculty_id = sanitize_string(request.form.get('faculty_id', '')).lower()

    if not faculty_id:
        flash("Please provide a Faculty ID.", "danger")
        return redirect(url_for('auth.forgot_password'))

    # Admin roles: show message instead of sending email
    if faculty_id in ('hod1', 'hod2', 'principal', 'admin', 'admin123'):
        flash("For Admin password reset, please contact the system administrator.", "info")
        return redirect(url_for('auth.forgot_password'))

    try:
        faculty = get_faculty_by_id(faculty_id)
        if not faculty:
            faculty = get_faculty_by_email(faculty_id)

        if faculty:
            fac_email = faculty.get('email')
            fac_pass = faculty.get('password')
            fac_name = faculty.get('name', 'Faculty')

            if fac_email:
                send_password_recovery_email(fac_name, fac_email, faculty_id, fac_pass)
                logger.info("Password recovery email sent for %s", faculty_id)

        # Always show generic success to prevent ID enumeration
        flash("If the Faculty ID exists, an email will be sent to the associated email address.", "success")
    except Exception as e:
        logger.error("Forgot password error: %s", e)
        flash("An error occurred. Please try again later.", "danger")

    return redirect(url_for('auth.forgot_password'))


@auth_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """Handle password changes for both faculty and admin users."""
    old_password = request.form.get('old_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not old_password or not new_password or not confirm_password:
        flash("All password fields are required.", "danger")
        return _redirect_to_user_dashboard()

    if new_password != confirm_password:
        flash("New passwords do not match.", "danger")
        return _redirect_to_user_dashboard()

    if len(new_password) < 6:
        flash("Password must be at least 6 characters.", "danger")
        return _redirect_to_user_dashboard()

    role = session['role']

    # ── Faculty password change ──
    if role == 'faculty':
        faculty_id = session.get('faculty_id')
        faculty = get_faculty_by_id(faculty_id)
        if not faculty:
            flash("Error retrieving your current data.", "danger")
            return redirect(url_for('faculty.faculty_dashboard'))

        if faculty.get('password') != old_password:
            flash("Incorrect current password.", "danger")
            return redirect(url_for('faculty.faculty_dashboard'))

        if update_faculty(faculty_id, {'password': new_password}):
            logger.info("Faculty %s changed password", faculty_id)
            flash("Password updated successfully!", "success")
        else:
            flash("Failed to update password.", "danger")

        return redirect(url_for('faculty.faculty_dashboard'))

    # ── Admin password change ──
    elif role in ('hod1', 'hod2', 'principal'):
        creds = get_admin_creds()
        if creds.get(role) != old_password:
            flash("Incorrect current password.", "danger")
            return redirect(url_for('dashboard.dashboard'))

        creds[role] = new_password
        if save_admin_creds(creds):
            logger.info("Admin %s changed password", role)
            flash("Password updated successfully!", "success")
        else:
            flash("Error saving new password.", "danger")

        return redirect(url_for('dashboard.dashboard'))

    return _redirect_to_user_dashboard()


@auth_bp.route('/change_username', methods=['POST'])
@login_required
def change_username():
    """Handle username changes for HOD users."""
    if session.get('role') not in ('hod1', 'hod2'):
        flash("Only HOD users can change usernames.", "danger")
        return redirect(url_for('auth.login'))

    current_username = session['role']
    new_username = sanitize_string(request.form.get('new_username', '')).lower()
    password = request.form.get('password', '')

    if not new_username or not password:
        flash("Username and password are required.", "danger")
        return redirect(url_for('dashboard.dashboard'))

    creds = get_admin_creds()
    if creds.get(current_username) != password:
        flash("Incorrect password.", "danger")
        return redirect(url_for('dashboard.dashboard'))

    if new_username in creds:
        flash(f"Username '{new_username}' is already taken.", "danger")
        return redirect(url_for('dashboard.dashboard'))

    try:
        creds[new_username] = creds.pop(current_username)
        if save_admin_creds(creds):
            session['role'] = new_username
            logger.info("Admin username changed: %s -> %s", current_username, new_username)
            flash(f"Username changed successfully to '{new_username}'!", "success")
        else:
            flash("Error saving new username.", "danger")
    except Exception as e:
        logger.error("Username change error: %s", e)
        flash(f"An error occurred: {str(e)}", "danger")
        creds[current_username] = creds.pop(new_username, creds.get(current_username))

    return redirect(url_for('dashboard.dashboard'))


@auth_bp.route('/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    """Handle profile picture upload."""
    import os
    from flask import current_app
    
    if 'avatar' not in request.files:
        flash('No file uploaded.', 'danger')
        return _redirect_to_user_dashboard()
        
    file = request.files['avatar']
    if file.filename == '':
        flash('No selected file.', 'danger')
        return _redirect_to_user_dashboard()
        
    if file:
        user_id = session.get('faculty_id') or session.get('role')
        if not user_id:
            flash('Session error.', 'danger')
            return _redirect_to_user_dashboard()
            
        filename = f"{user_id}.jpg"
        upload_dir = os.path.join(current_app.static_folder, 'uploads', 'avatars')
        os.makedirs(upload_dir, exist_ok=True)
        
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        flash('Profile picture updated successfully!', 'success')
        
    return _redirect_to_user_dashboard()


def _redirect_to_user_dashboard():
    """Helper to redirect user to their appropriate dashboard."""
    role = session.get('role', '')
    if role in ('hod1', 'hod2', 'principal'):
        return redirect(url_for('dashboard.dashboard'))
    elif role == 'faculty':
        return redirect(url_for('faculty.faculty_dashboard'))
    return redirect(url_for('auth.login'))
