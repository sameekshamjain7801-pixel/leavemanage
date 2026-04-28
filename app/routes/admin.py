"""
Admin management routes blueprint.
Handles faculty CRUD operations by HOD/Principal.
"""

import logging
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app

from app.services.db_service import (
    get_all_faculty,
    get_faculty_by_id,
    create_faculty as db_create_faculty,
    update_faculty as db_update_faculty,
    delete_faculty as db_delete_faculty,
)
from app.utils.email_service import send_registration_email
from app.utils.decorators import admin_required
from app.utils.validators import sanitize_string, validate_email, validate_password

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/manage_faculty')
@admin_required
def manage_faculty():
    """Display faculty management page."""
    faculty_list = get_all_faculty()
    logger.debug("Loaded %d faculty for management", len(faculty_list))
    return render_template('hod_faculty_management.html', faculty_list=faculty_list)


@admin_bp.route('/create_faculty', methods=['POST'])
@admin_required
def create_faculty():
    """Create a new faculty account."""
    faculty_id = sanitize_string(request.form.get('faculty_id', '')).lower()
    name = sanitize_string(request.form.get('name', ''))
    email = sanitize_string(request.form.get('email', ''))
    department = sanitize_string(request.form.get('department', ''))
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')

    # Parse leave quota
    try:
        leave_quota = int(request.form.get('leave_quota', 20))
        if leave_quota < 1 or leave_quota > 365:
            leave_quota = 20
    except (ValueError, TypeError):
        leave_quota = 20

    # Validation
    if not all([faculty_id, name, email, department, password]):
        flash("All fields are required.", "danger")
        return redirect(url_for('admin.manage_faculty'))

    if not validate_email(email):
        flash("Please enter a valid email address.", "danger")
        return redirect(url_for('admin.manage_faculty'))

    is_valid, msg = validate_password(password)
    if not is_valid:
        flash(msg, "danger")
        return redirect(url_for('admin.manage_faculty'))

    # Check for duplicate faculty ID
    existing = get_faculty_by_id(faculty_id)
    if existing:
        flash(f"Faculty ID '{faculty_id}' already exists.", "danger")
        return redirect(url_for('admin.manage_faculty'))

    payload = {
        'faculty_id': faculty_id,
        'name': name,
        'email': email,
        'department': department,
        'password': password,
        'leave_quota': leave_quota,
    }

    if db_create_faculty(payload):
        logger.info("Faculty created: %s by %s", faculty_id, session.get('role'))

        # Send welcome email (Asynchronous to avoid blocking)
        try:
            from app.utils.email_service import send_email_async
            subject = "Welcome to LeaveFlow - Your Faculty Account"
            body = f"Dear {name},\n\nWelcome to LeaveFlow! Your account has been created.\n\nFaculty ID: {faculty_id}\nPassword: {password}\n\nPlease login at: {current_app.config.get('APP_URL')}"
            send_email_async(email, subject, body)
        except Exception as e:
            logger.error("Registration email background queue failed: %s", e)

        flash(f"Faculty '{name}' created successfully! Email sent to {email}", "success")
    else:
        flash(f"Failed to save faculty '{name}' to database.", "danger")

    return redirect(url_for('admin.manage_faculty'))


@admin_bp.route('/update_faculty', methods=['POST'])
@admin_required
def update_faculty():
    """Update an existing faculty record."""
    faculty_id = sanitize_string(request.form.get('faculty_id', ''))
    name = sanitize_string(request.form.get('name', ''))
    email = sanitize_string(request.form.get('email', ''))
    department = sanitize_string(request.form.get('department', ''))

    try:
        leave_quota = int(request.form.get('leave_quota', 20))
        if leave_quota < 1 or leave_quota > 365:
            leave_quota = 20
    except (ValueError, TypeError):
        leave_quota = 20

    if not all([faculty_id, name, email, department]):
        flash("All fields are required.", "danger")
        return redirect(url_for('admin.manage_faculty'))

    update_data = {
        'name': name,
        'email': email,
        'department': department,
        'leave_quota': leave_quota,
    }

    if db_update_faculty(faculty_id, update_data):
        logger.info("Faculty %s updated by %s", faculty_id, session.get('role'))
        flash(f"Faculty updated successfully! Leave quota set to {leave_quota} days.", "success")
    else:
        flash("Faculty update failed. Please try again.", "danger")

    return redirect(url_for('admin.manage_faculty'))


@admin_bp.route('/delete_faculty/<faculty_id>')
@admin_required
def delete_faculty(faculty_id):
    """Delete a faculty record."""
    faculty_id = sanitize_string(faculty_id)

    if db_delete_faculty(faculty_id):
        logger.info("Faculty %s deleted by %s", faculty_id, session.get('role'))
        flash("Faculty deleted successfully!", "success")
    else:
        flash("Failed to delete faculty.", "danger")

    return redirect(url_for('admin.manage_faculty'))


@admin_bp.route('/faculty/<identifier>')
@admin_required
def faculty_profile(identifier):
    """View detailed profile and leave history for a specific faculty member."""
    from app.services.db_service import get_leave_requests_by_email, get_faculty_by_email
    from app.services.leave_service import get_user_leave_balances
    
    # Try by ID first, then by Email
    faculty = get_faculty_by_id(identifier)
    if not faculty:
        faculty = get_faculty_by_email(identifier)
        
    if not faculty:
        flash("Faculty not found.", "danger")
        return redirect(url_for('admin.manage_faculty'))
    
    email = faculty.get('email')
    quota = int(faculty.get('leave_quota') or 20)
    
    # Fetch all leave requests for this faculty
    leave_history = get_leave_requests_by_email(email)
    
    # Calculate balance
    balances = get_user_leave_balances([email], {email: quota})
    balance = balances.get(email, {'used': 0, 'available': quota, 'quota': quota})
    
    # Sort history by date (newest first)
    leave_history.sort(key=lambda x: x.get('from_date', ''), reverse=True)
    
    return render_template(
        'faculty_profile.html',
        faculty=faculty,
        leave_history=leave_history,
        balance=balance
    )


@admin_bp.route('/all_pending')
@admin_required
def all_pending():
    """Display a comprehensive list of all pending leave requests."""
    from app.services.db_service import get_all_leave_requests
    all_reqs = get_all_leave_requests()
    
    # Filter for pending requests
    pending = [req for req in all_reqs if req.get('status') == 'Pending' or req.get('status') == 'HOD Approved' and session.get('role') == 'principal']
    # Sort by date (newest first)
    pending.sort(key=lambda x: x.get('from_date', ''), reverse=True)
    
    return render_template('admin_all_pending.html', pending_requests=pending)


@admin_bp.route('/all_history')
@admin_required
def all_history():
    """Display a comprehensive list of all historical leave records."""
    from app.services.db_service import get_all_leave_requests
    all_reqs = get_all_leave_requests()
    
    # Filter for processed requests
    history = [req for req in all_reqs if req.get('status') != 'Pending']
    # Sort by date (newest first)
    history.sort(key=lambda x: x.get('from_date', ''), reverse=True)
    
    return render_template('admin_all_history.html', history_requests=history)


@admin_bp.route('/department_overview')
@admin_required
def department_overview():
    """Display leave analytics by department based on real database records."""
    from app.services.db_service import get_all_leave_requests
    all_requests = get_all_leave_requests()
    
    # Calculate counts by department
    dept_stats = {}
    for req in all_requests:
        dept = req.get('department', 'Other')
        dept_stats[dept] = dept_stats.get(dept, 0) + 1
    
    # Convert to list for template
    colors = ['#4f46e5', '#818cf8', '#10b981', '#f59e0b', '#ef4444', '#0ea5e9']
    depts_list = []
    for i, (name, count) in enumerate(dept_stats.items()):
        depts_list.append({
            'name': name,
            'count': count,
            'color': colors[i % len(colors)]
        })
        
    # Sort by count (descending)
    depts_list.sort(key=lambda x: x['count'], reverse=True)
    
    return render_template('department_overview.html', depts=depts_list)


@admin_bp.route('/calendar')
@admin_required
def leave_calendar():
    """Display leave calendar with real approved requests."""
    from app.services.db_service import get_all_leave_requests
    all_reqs = get_all_leave_requests()
    
    # Filter for approved and pending leaves
    calendar_leaves = []
    for req in all_reqs:
        status = req.get('status', '')
        if 'Approved' in status:
            leave_type = 'Approved'
        elif status == 'Pending':
            leave_type = 'Pending'
        else:
            continue
            
        calendar_leaves.append({
            'name': req.get('student_name', 'Faculty'),
            'department': req.get('department', 'Unknown Dept'),
            'from_date': req.get('from_date', ''),
            'to_date': req.get('to_date', ''),
            'type': leave_type,
            'status': status,
            'reason': req.get('reason', 'No reason provided')
        })
            
    from datetime import datetime, timedelta
    import calendar
    
    today_dt = datetime.now()
    tomorrow_dt = today_dt + timedelta(days=1)
    
    try:
        req_year = int(request.args.get('year', today_dt.year))
        req_month = int(request.args.get('month', today_dt.month))
    except (ValueError, TypeError):
        req_year = today_dt.year
        req_month = today_dt.month

    # Make sure month is valid
    if req_month < 1:
        req_month = 12
        req_year -= 1
    elif req_month > 12:
        req_month = 1
        req_year += 1
        
    year = req_year
    month = req_month
    
    current_month_dt = datetime(year, month, 1)
    current_month_str = current_month_dt.strftime("%B %Y")
    
    # Calculate previous and next months
    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year
        
    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year
    
    cal = calendar.Calendar(firstweekday=0) # Monday is 0
    month_days = cal.monthdayscalendar(year, month)
    
    return render_template('leave_calendar.html', 
                           leaves=calendar_leaves,
                           today_str=today_dt.strftime("%Y-%m-%d"),
                           tomorrow_str=tomorrow_dt.strftime("%Y-%m-%d"),
                           current_month_str=current_month_str,
                           month_days=month_days,
                           year=year,
                           month=month,
                           prev_year=prev_year,
                           prev_month=prev_month,
                           next_year=next_year,
                           next_month=next_month)


@admin_bp.route('/settings')
@admin_required
def settings():
    """Display system settings."""
    return render_template('settings.html')
