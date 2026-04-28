"""
Faculty routes blueprint.
Handles faculty dashboard and leave submission.
"""

import logging
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from app.services.db_service import (
    get_leave_requests_by_email,
    create_leave_request,
    get_faculty_by_email,
)
from app.services.leave_service import get_user_leave_balances
from app.utils.decorators import faculty_required
from app.utils.validators import sanitize_string, validate_date

logger = logging.getLogger(__name__)

faculty_bp = Blueprint('faculty', __name__)


@faculty_bp.route('/faculty_dashboard')
@faculty_required
def faculty_dashboard():
    """Faculty member's dashboard showing their leave requests and balances."""
    faculty_email = session.get('faculty_email')

    try:
        all_requests = get_leave_requests_by_email(faculty_email)

        my_requests = []
        history_requests = []
        notifications = []
        current_notif_ids = []
        dismissed_ids = session.get('dismissed_notification_ids', [])

        for req in all_requests:
            req_id = req.get('id')
            if req['status'] == 'Pending':
                my_requests.append(req)
            else:
                history_requests.append(req)
                if req_id not in dismissed_ids:
                    notifications.append(
                        f"Update: Request ({req.get('from_date')} to {req.get('to_date')}) "
                        f"is now {req.get('status')}"
                    )
                    current_notif_ids.append(req_id)
        
        session['current_notification_ids'] = current_notif_ids

        # Fetch leave quota
        fac_quota = 20
        try:
            fac_record = get_faculty_by_email(faculty_email)
            if fac_record:
                fac_quota = int(fac_record.get('leave_quota') or 20)
        except Exception:
            pass

        balance_info = get_user_leave_balances(
            [faculty_email],
            {faculty_email: fac_quota}
        ).get(faculty_email, {'used': 0, 'available': fac_quota, 'quota': fac_quota})

    except Exception as e:
        logger.error("Faculty dashboard error: %s", e)
        flash(f"Error fetching requests: {str(e)}", "danger")
        my_requests = []
        history_requests = []
        balance_info = {'used': 0, 'available': 20, 'quota': 20}
        notifications = []

    from datetime import date
    today_str = date.today().isoformat()

    return render_template(
        'faculty_submission.html',
        faculty_name=session.get('faculty_name'),
        faculty_email=session.get('faculty_email'),
        faculty_department=session.get('faculty_department'),
        my_requests=my_requests,
        history_requests=history_requests,
        balance_info=balance_info,
        notifications=notifications,
        today_date=today_str,
    )


@faculty_bp.route('/submit_leave', methods=['POST'])
@faculty_required
def submit_leave():
    """Handle faculty leave request submission."""
    student_name = sanitize_string(request.form.get('student_name', ''))
    email = sanitize_string(request.form.get('email', ''))
    department = sanitize_string(request.form.get('department', ''))
    reason = sanitize_string(request.form.get('reason', ''))
    from_date = request.form.get('from_date', '')
    to_date = request.form.get('to_date', '')
    leave_type = request.form.get('leave_type', 'full_day')
    from_time = request.form.get('from_time', '')
    to_time = request.form.get('to_time', '')

    # Set to_date to from_date if missing (half day)
    if not to_date:
        to_date = from_date

    # Validate required fields
    if not all([student_name, email, department, reason, from_date, to_date]):
        flash("All fields are required.", "danger")
        return redirect(url_for('faculty.faculty_dashboard'))

    if not validate_date(from_date) or not validate_date(to_date):
        flash("Invalid date format.", "danger")
        return redirect(url_for('faculty.faculty_dashboard'))

    # Check for today or future date
    from datetime import date
    today_str = date.today().isoformat()
    
    if from_date < today_str:
        flash("Leave cannot be applied for past dates.", "danger")
        return redirect(url_for('faculty.faculty_dashboard'))

    # Build reason for half-day
    if leave_type == 'half_day':
        reason = f"{reason} (Half Day: {from_time} to {to_time})"

    payload = {
        'student_name': student_name,
        'email': email,
        'department': department,
        'reason': reason,
        'from_date': from_date,
        'to_date': to_date,
        'status': 'Pending',
    }

    if create_leave_request(payload):
        leave_type_text = "Half Day" if leave_type == 'half_day' else "Full Day"
        if leave_type == 'half_day' and from_time and to_time:
            flash(f"Leave request submitted successfully! ({leave_type_text}: {from_time} to {to_time})", "success")
        else:
            flash(f"Leave request submitted successfully! ({leave_type_text})", "success")
        logger.info("Leave submitted by %s: %s to %s", email, from_date, to_date)
    else:
        flash("Submission failed. Please try again.", "danger")

    return redirect(url_for('faculty.faculty_dashboard'))
