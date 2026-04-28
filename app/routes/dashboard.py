"""
Dashboard routes blueprint.
Handles HOD/Principal dashboard, leave processing, and history management.
"""

import json
import logging
import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from app.services.db_service import (
    get_all_leave_requests,
    get_leave_request_by_id,
    update_leave_request,
)
from app.services.leave_service import get_user_leave_balances, get_quotas_for_emails
from app.utils.email_service import send_email, send_leave_notification
from app.utils.decorators import admin_required
from app.utils.validators import sanitize_string

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__)

# Archived requests file path
ARCHIVED_REQS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'archived_requests.json')


def _get_archived_reqs() -> list:
    """Load archived request IDs from file."""
    if os.path.exists(ARCHIVED_REQS_FILE):
        try:
            with open(ARCHIVED_REQS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error("Error reading archived requests: %s", e)
    return []


def _add_archived_reqs(req_ids: list) -> bool:
    """Add request IDs to the archive."""
    current = _get_archived_reqs()
    updated = list(set(current + req_ids))
    try:
        with open(ARCHIVED_REQS_FILE, 'w') as f:
            json.dump(updated, f)
        return True
    except Exception as e:
        logger.error("Error saving archived requests: %s", e)
        return False


@dashboard_bp.route('/dashboard')
@admin_required
def dashboard():
    """HOD/Principal dashboard showing pending and history requests."""
    role = session['role']

    try:
        all_data = get_all_leave_requests()
        archived = _get_archived_reqs()

        pending_requests = []
        history_requests = []
        notifications = []
        current_notif_ids = []
        dismissed_ids = session.get('dismissed_notification_ids', [])

        for req in all_data:
            req_id = req.get('id')

            if role in ('hod1', 'hod2'):
                if req['status'] == 'Pending':
                    pending_requests.append(req)
                    if req_id not in dismissed_ids:
                        notifications.append(f"New pending request from {req.get('student_name')}")
                        current_notif_ids.append(req_id)
                elif req['status'] in ('HOD Approved', 'Principal Approved', 'Rejected'):
                    if req_id not in archived:
                        history_requests.append(req)

            elif role == 'principal':
                if req['status'] == 'HOD Approved':
                    pending_requests.append(req)
                    if req_id not in dismissed_ids:
                        notifications.append(f"HOD Approved request from {req.get('student_name')}")
                        current_notif_ids.append(req_id)
                elif req['status'] in ('Principal Approved', 'Rejected'):
                    if req_id not in archived:
                        history_requests.append(req)

        session['current_notification_ids'] = current_notif_ids

        # Fetch leave balances for pending requests
        pending_emails = list(set(r['email'] for r in pending_requests if r.get('email')))
        quotas = get_quotas_for_emails(pending_emails)
        leave_balances = get_user_leave_balances(pending_emails, quotas)

        # Fetch all faculty for search/profile feature
        from app.services.db_service import get_all_faculty
        faculty_list = get_all_faculty()

        # ── Calculate real data for Linebar (Last 6 months) ──
        chart_labels = []
        approved_data = []
        pending_data = []
        
        from datetime import datetime, timedelta
        now = datetime.now()
        
        for i in range(5, -1, -1):
            month_date = now - timedelta(days=i*30)
            month_label = month_date.strftime('%b')
            chart_labels.append(month_label)
            
            # Count for this month
            month_approved = 0
            month_pending = 0
            
            for req in all_data:
                try:
                    req_date = datetime.strptime(req.get('from_date', ''), '%Y-%m-%d')
                    if req_date.month == month_date.month and req_date.year == month_date.year:
                        if req['status'] in ('Principal Approved', 'HOD Approved'):
                            month_approved += 1
                        elif req['status'] == 'Pending':
                            month_pending += 1
                except:
                    continue
            
            approved_data.append(month_approved)
            pending_data.append(month_pending)
        
        chart_data = {
            'labels': chart_labels,
            'approved': approved_data,
            'pending': pending_data
        }

    except Exception as e:
        logger.error("Dashboard error: %s", e)
        flash(f"System Error: {str(e)}", "danger")
        pending_requests = []
        history_requests = []
        leave_balances = {}
        notifications = []
        faculty_list = []
        scaled_bars = [10] * 12

    view = request.args.get('view', 'dashboard')
    
    return render_template(
        'dashboard.html',
        requests=pending_requests,
        history_requests=history_requests,
        leave_balances=leave_balances,
        notifications=notifications,
        faculty_list=faculty_list,
        chart_data = chart_data,
        view=view
    )


@dashboard_bp.route('/process_leave', methods=['POST'])
@admin_required
def process_leave():
    """Handle approve/reject/send_email actions on leave requests."""
    req_id = request.form.get('id')
    action = request.form.get('action')
    remarks = sanitize_string(request.form.get('remarks', ''))
    email_body = request.form.get('email_body', '')
    role = session['role']

    if role == 'principal' and action in ('approve', 'reject'):
        flash("Principal accounts currently have read-only access and cannot process leave requests.", "warning")
        return redirect(url_for('dashboard.dashboard'))

    # ── Manual email trigger ──
    if action == 'send_email':
        req_data = get_leave_request_by_id(req_id)
        if req_data:
            from app.utils.email_service import send_email_async
            receiver_email = req_data.get('email')
            final_body = email_body.replace("[WILL BE UPDATED ON ACTION]", req_data.get('status', ''))
            subject = f"Leave Request Update - {req_data.get('student_name', 'Faculty')}"
            
            # Use async send to avoid blocking the UI
            send_email_async(receiver_email, subject, final_body)
            flash("Professional email is being dispatched in the background.", "success")
        else:
            flash("Leave request not found.", "danger")
        return redirect(url_for('dashboard.dashboard'))

    # ── Approve / Reject ──
    if role in ('hod1', 'hod2'):
        new_status = "HOD Approved" if action == 'approve' else "Rejected"
        update_data = {
            'status': new_status,
            'hod_remarks': remarks,
            'hod_email_body': email_body,
        }
    else:
        new_status = "Principal Approved" if action == 'approve' else "Rejected"
        update_data = {
            'status': new_status,
            'principal_remarks': remarks,
            'principal_email_body': email_body,
        }

    if update_leave_request(req_id, update_data):
        logger.info("Leave %s %s by %s", req_id, new_status, role)
        flash(f"Request {new_status} successfully!", "success")

        # Auto-send notification email (Asynchronous)
        try:
            req_data = get_leave_request_by_id(req_id)
            if req_data:
                from app.utils.email_service import build_leave_notification_html, send_email_async
                faculty_email = req_data.get('email')
                subject = f"Leave Request {new_status} – {req_data.get('from_date', '')}"
                plain_body = f"Your leave request for {req_data.get('from_date', '')} has been {new_status}."
                html_body = build_leave_notification_html(req_data, new_status, role, remarks)
                
                # Send in background
                send_email_async(faculty_email, subject, plain_body, html_body)
                flash(f"Status updated. Notification email to {faculty_email} is being sent.", "info")
        except Exception as e:
            logger.error("Auto-email background queue failed: %s", e)
    else:
        flash("Failed to update leave request. Please try again.", "danger")

    return redirect(url_for('dashboard.dashboard'))


@dashboard_bp.route('/edit_leave', methods=['POST'])
@admin_required
def edit_leave():
    """Allow HOD to edit leave request details."""
    req_id = request.form.get('id')
    update_data = {
        'student_name': sanitize_string(request.form.get('student_name', '')),
        'email': sanitize_string(request.form.get('email', '')),
        'department': sanitize_string(request.form.get('department', '')),
        'reason': sanitize_string(request.form.get('reason', '')),
        'from_date': request.form.get('from_date', ''),
        'to_date': request.form.get('to_date', ''),
    }

    if update_leave_request(req_id, update_data):
        flash("Leave request updated successfully!", "success")
    else:
        flash("Failed to update leave request.", "danger")

    return redirect(url_for('dashboard.dashboard'))


@dashboard_bp.route('/clear_history', methods=['POST'])
@admin_required
def clear_history():
    """Clear processed requests from dashboard view (archive them)."""
    role = session['role']

    try:
        all_data = get_all_leave_requests()
        to_archive = []

        for req in all_data:
            if role in ('hod1', 'hod2') and req['status'] in ('HOD Approved', 'Principal Approved', 'Rejected'):
                to_archive.append(req['id'])
            elif role == 'principal' and req['status'] in ('Principal Approved', 'Rejected'):
                to_archive.append(req['id'])

        if to_archive:
            _add_archived_reqs(to_archive)
            logger.info("%s archived %d records", role, len(to_archive))
            flash(f"Successfully cleared {len(to_archive)} historical records from view.", "success")
        else:
            flash("No history available to clear.", "info")
    except Exception as e:
        logger.error("Clear history error: %s", e)
        flash(f"Error clearing history: {str(e)}", "danger")

    return redirect(url_for('dashboard.dashboard'))
