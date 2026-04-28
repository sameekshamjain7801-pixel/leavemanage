"""
Leave balance and business logic service.
"""

import logging
from datetime import datetime
from app.services.db_service import get_approved_leave_requests, get_faculty_by_emails

logger = logging.getLogger(__name__)


def count_leave_days(from_str: str, to_str: str) -> int:
    """Calculate the number of leave days between two date strings."""
    try:
        f = datetime.strptime(from_str, "%Y-%m-%d")
        t = datetime.strptime(to_str, "%Y-%m-%d")
        return max(0, (t - f).days + 1)
    except (ValueError, TypeError):
        return 0


def get_user_leave_balances(emails: list, quotas: dict = None) -> dict:
    """
    Calculate leave balances for a list of faculty emails.
    Optimized to minimize database scans.
    """
    if not emails:
        return {}

    if quotas is None:
        quotas = {}

    default_quota = 20
    balances = {email: {'used': 0.0, 'available': float(quotas.get(email, default_quota)), 'quota': quotas.get(email, default_quota)} for email in emails}

    try:
        # get_approved_leave_requests is now cached per-request
        approved = get_approved_leave_requests()
        for req in approved:
            em = req.get('email')
            if em in balances:
                days = count_leave_days(req.get('from_date'), req.get('to_date'))
                # Half-day detection
                if req.get('leave_type') == 'half_day' or '(Half Day' in req.get('reason', ''):
                    days = 0.5
                balances[em]['used'] += float(days)
        
        # Final calculation pass
        for em in balances:
            balances[em]['available'] = max(0.0, float(balances[em]['quota']) - balances[em]['used'])
            
    except Exception as e:
        logger.error("Error calculating leave balances: %s", e)

    return balances


def get_quotas_for_emails(emails: list, default_quota: int = 20) -> dict:
    """Fetch per-faculty leave quotas from the database."""
    quotas = {}
    if not emails:
        return quotas

    try:
        faculty_records = get_faculty_by_emails(emails)
        for fac in faculty_records:
            quotas[fac['email']] = int(fac.get('leave_quota') or default_quota)
    except Exception as e:
        logger.error("Error fetching quotas: %s", e)

    return quotas
