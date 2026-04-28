"""
Reusable SMTP email service with TLS support.
Supports both plain-text and HTML emails.
Uses background threading for non-blocking sends.
"""

import logging
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from flask import current_app

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str, html: str = None) -> bool:
    """
    Send an email via SMTP SSL.

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.
        html: Optional HTML body (multipart alternative).

    Returns:
        True if sent successfully, False otherwise.
    """
    smtp_email = current_app.config['SMTP_EMAIL']
    smtp_password = current_app.config['SMTP_PASSWORD']
    smtp_host = current_app.config['SMTP_HOST']
    smtp_port = current_app.config['SMTP_PORT']
    sender_name = current_app.config['SMTP_SENDER_NAME']

    if not smtp_email or not smtp_password:
        logger.error("SMTP credentials not configured. Set SMTP_EMAIL and SMTP_PASSWORD.")
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{sender_name} <{smtp_email}>"
        msg['To'] = to
        msg['Subject'] = subject

        # Always attach plain text
        msg.attach(MIMEText(body, 'plain'))

        # Attach HTML if provided
        if html:
            msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15) as server:
            server.login(smtp_email, smtp_password)
            server.send_message(msg)

        logger.info("Email sent to %s: %s", to, subject)
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed. Check email/password credentials.")
        return False
    except smtplib.SMTPException as e:
        logger.error("SMTP error sending email to %s: %s", to, e)
        return False
    except Exception as e:
        logger.error("Unexpected error sending email to %s: %s", to, e)
        return False


def send_email_async(to: str, subject: str, body: str, html: str = None, app=None):
    """
    Send an email in a background thread (non-blocking).

    Args:
        to: Recipient email address.
        subject: Email subject line.
        body: Plain-text email body.
        html: Optional HTML body.
        app: Flask app instance (required for app context in thread).
    """
    if app is None:
        app = current_app._get_current_object()

    def _send():
        with app.app_context():
            send_email(to, subject, body, html)

    thread = threading.Thread(target=_send, name=f"email-{to[:20]}")
    thread.daemon = True
    thread.start()
    logger.debug("Async email queued for %s", to)


def build_leave_notification_html(req_data: dict, new_status: str, role: str, remarks: str = '') -> str:
    """
    Build a professional HTML email for leave request status updates.

    Args:
        req_data: Leave request data dict from Supabase.
        new_status: The new status string (e.g., 'HOD Approved').
        role: The approver's role (e.g., 'hod1', 'principal').
        remarks: Optional approver remarks.

    Returns:
        HTML string for the email body.
    """
    faculty_name = req_data.get('student_name', 'Faculty member')
    from_date = req_data.get('from_date', '')
    to_date = req_data.get('to_date', '')
    reason = req_data.get('reason', '')

    status_color = "#198754" if "Approved" in new_status else "#dc3545"
    status_icon = "✓" if "Approved" in new_status else "✕"

    # Get app URL from config (with fallback)
    try:
        app_url = current_app.config.get('APP_URL', 'http://127.0.0.1:5000')
    except RuntimeError:
        app_url = 'http://127.0.0.1:5000'

    remarks_html = ""
    if remarks:
        remarks_html = f"""
        <div class="remarks"><strong>Approver Remarks:</strong><br>{remarks}</div>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 20px auto; border: 1px solid #eee; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }}
            .header {{ background: linear-gradient(135deg, #8b5cf6, #7c3aed); color: white; padding: 30px; text-align: center; }}
            .content {{ padding: 30px; background: #ffffff; }}
            .status-badge {{ display: inline-block; padding: 8px 16px; border-radius: 50px; background-color: {status_color}; color: white; font-weight: bold; margin-bottom: 20px; }}
            .details {{ background: #f8fafc; border-radius: 8px; padding: 20px; margin-bottom: 20px; }}
            .details-row {{ display: table; width: 100%; margin-bottom: 10px; border-bottom: 1px solid #edf2f7; padding-bottom: 10px; }}
            .label {{ display: table-cell; width: 120px; font-weight: bold; color: #64748b; font-size: 14px; text-transform: uppercase; }}
            .value {{ display: table-cell; color: #1e293b; font-size: 15px; }}
            .remarks {{ border-left: 4px solid #e2e8f0; padding-left: 15px; margin-top: 20px; font-style: italic; color: #475569; }}
            .footer {{ background: #f1f5f9; padding: 20px; text-align: center; font-size: 12px; color: #94a3b8; }}
            .btn {{ display: inline-block; padding: 12px 24px; background: #8b5cf6; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin:0; font-size: 24px;">LeaveFlow</h1>
                <p style="margin:5px 0 0; opacity: 0.8;">Leave Management System</p>
            </div>
            <div class="content">
                <div style="text-align: center;">
                    <div class="status-badge">{status_icon} {new_status}</div>
                </div>
                <p>Dear <strong>{faculty_name}</strong>,</p>
                <p>Your leave request has been processed by the <strong>{role.upper()}</strong>. Below are the finalized details:</p>

                <div class="details">
                    <div class="details-row">
                        <div class="label">Duration</div>
                        <div class="value">{from_date} to {to_date}</div>
                    </div>
                    <div class="details-row">
                        <div class="label">Reason</div>
                        <div class="value">{reason}</div>
                    </div>
                    <div class="details-row" style="border:none; padding: 0;">
                        <div class="label">Decision</div>
                        <div class="value" style="color: {status_color}; font-weight: bold;">{new_status}</div>
                    </div>
                </div>

                {remarks_html}

                <div style="text-align: center; margin-top: 30px;">
                    <a href="{app_url}" class="btn">View Dashboard</a>
                </div>
            </div>
            <div class="footer">
                This is an automated notification from LeaveFlow.<br>
                &copy; {datetime.now().year} LeaveFlow Administration
            </div>
        </div>
    </body>
    </html>
    """
    return html


def build_welcome_email_html(name: str, faculty_id: str, password: str, app_url: str) -> str:
    """
    Build a professional HTML email for welcoming new faculty members.
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f8fafc; }}
            .container {{ max-width: 600px; margin: 40px auto; background: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.05); }}
            .header {{ background: linear-gradient(135deg, #4f46e5, #3b82f6); color: white; padding: 40px 30px; text-align: center; }}
            .header-icon {{ font-size: 48px; margin-bottom: 10px; }}
            .content {{ padding: 40px 30px; }}
            .welcome-title {{ font-size: 24px; font-weight: bold; color: #1e293b; margin-top: 0; margin-bottom: 20px; }}
            .credentials-box {{ background: #f1f5f9; border-radius: 12px; padding: 25px; margin: 30px 0; border-left: 5px solid #4f46e5; }}
            .cred-row {{ margin-bottom: 15px; font-size: 16px; }}
            .cred-row:last-child {{ margin-bottom: 0; }}
            .cred-label {{ font-weight: bold; color: #64748b; display: inline-block; width: 100px; }}
            .cred-value {{ font-family: monospace; font-size: 18px; color: #0f172a; font-weight: bold; background: #e2e8f0; padding: 4px 8px; border-radius: 4px; }}
            .btn-container {{ text-align: center; margin: 40px 0 20px; }}
            .btn {{ display: inline-block; padding: 14px 32px; background: #4f46e5; color: white; text-decoration: none; border-radius: 50px; font-weight: bold; font-size: 16px; transition: background 0.3s; box-shadow: 0 4px 6px rgba(79, 70, 229, 0.2); }}
            .btn:hover {{ background: #4338ca; }}
            .footer {{ background: #f8fafc; padding: 25px; text-align: center; font-size: 13px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
            .steps {{ margin-top: 30px; padding-left: 20px; color: #475569; }}
            .steps li {{ margin-bottom: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="header-icon">🎓</div>
                <h1 style="margin:0; font-size: 28px; font-weight: 800; letter-spacing: -0.5px;">LeaveFlow</h1>
                <p style="margin:8px 0 0; opacity: 0.9; font-size: 16px;">Faculty Leave Management System</p>
            </div>
            <div class="content">
                <h2 class="welcome-title">Welcome aboard, {name}!</h2>
                <p style="font-size: 16px; color: #475569;">Your HOD has successfully created your faculty account on <strong>LeaveFlow</strong>. You can now log in to manage, track, and submit your leave requests seamlessly.</p>
                
                <div class="credentials-box">
                    <div style="margin-bottom: 15px; font-size: 14px; text-transform: uppercase; color: #4f46e5; font-weight: 800; letter-spacing: 1px;">Your Login Credentials</div>
                    <div class="cred-row">
                        <span class="cred-label">Faculty ID:</span>
                        <span class="cred-value">{faculty_id}</span>
                    </div>
                    <div class="cred-row">
                        <span class="cred-label">Password:</span>
                        <span class="cred-value">{password}</span>
                    </div>
                </div>
                
                <h3 style="color: #1e293b; margin-top: 30px;">Next Steps:</h3>
                <ol class="steps">
                    <li>Click the button below to access the LeaveFlow dashboard.</li>
                    <li>Log in using your Faculty ID and the temporary password provided above.</li>
                    <li>For your security, please change your password immediately from your account settings.</li>
                </ol>
                
                <div class="btn-container">
                    <a href="{app_url}" class="btn">Login to LeaveFlow</a>
                </div>
            </div>
            <div class="footer">
                This is an automated notification from LeaveFlow.<br>
                Please do not reply to this email.<br><br>
                &copy; {datetime.now().year} LeaveFlow Administration
            </div>
        </div>
    </body>
    </html>
    """
    return html


def send_leave_notification(req_data: dict, new_status: str, role: str, remarks: str = '') -> bool:
    """
    Send a professional leave notification email.

    Args:
        req_data: Leave request data dict.
        new_status: New status string.
        role: Approver's role.
        remarks: Optional approver remarks.

    Returns:
        True if sent, False otherwise.
    """
    faculty_email = req_data.get('email')
    faculty_name = req_data.get('student_name', 'Faculty member')
    from_date = req_data.get('from_date', '')
    to_date = req_data.get('to_date', '')

    if not faculty_email:
        logger.error("Cannot send notification: no email in request data")
        return False

    subject = f"Leave Request {new_status} – {from_date}"
    plain_body = f"Your leave request for {from_date} to {to_date} has been {new_status}."
    html_body = build_leave_notification_html(req_data, new_status, role, remarks)

    return send_email(faculty_email, subject, plain_body, html_body)


def send_registration_email(name: str, email: str, faculty_id: str, password: str) -> bool:
    """
    Send a welcome email to newly registered faculty.
    """
    try:
        app_url = current_app.config.get('APP_URL', 'http://127.0.0.1:5000')
    except RuntimeError:
        app_url = 'http://127.0.0.1:5000'

    subject = "Welcome to LeaveFlow - Your Faculty Account"
    body = f"""Dear {name},

Welcome to LeaveFlow - Faculty Leave Management System!

Your account has been created by the HOD. Here are your login credentials:

Faculty ID: {faculty_id}
Password: {password}
URL: {app_url}

IMPORTANT:
1. Please log in immediately using the credentials above
2. Change your password after first login
3. For any issues, contact your HOD

Workflow:
- Submit leave requests through your faculty dashboard
- HOD will review and forward to Principal
- You will receive email notifications at each step

Best regards,
LeaveFlow Administration
"""
    return send_email(email, subject, body)


def send_password_recovery_email(name: str, email: str, faculty_id: str, password: str) -> bool:
    """
    Send a password recovery email to a faculty member.
    """
    subject = "Your LeaveFlow Password"
    body = (
        f"Hello {name},\n\n"
        f"Your Faculty ID is: {faculty_id}\n"
        f"Your password is: {password}\n\n"
        f"Please switch to a secure password after logging in."
    )
    return send_email(email, subject, body)
