"""
Supabase database service layer.
All database operations go through this module for clean separation of concerns.
"""

import logging
from typing import Optional
import time
import requests
from flask import current_app

logger = logging.getLogger(__name__)

# Simple in-memory cache to reduce Supabase latency
_cache = {
    'leave_requests': {'data': None, 'time': 0},
    'faculty_list': {'data': None, 'time': 0}
}
CACHE_TTL = 30 # Seconds

# Module-level session for connection reuse
_http_session = requests.Session()


def _get_headers(content_type: bool = False, prefer_minimal: bool = False) -> dict:
    """Build standard Supabase REST API headers."""
    key = current_app.config['SUPABASE_KEY']
    headers = {
        'apikey': key,
        'Authorization': f'Bearer {key}',
    }
    if content_type:
        headers['Content-Type'] = 'application/json'
    if prefer_minimal:
        headers['Prefer'] = 'return=minimal'
    return headers


def _leave_url() -> str:
    return current_app.config['SUPABASE_LEAVE_URL']


def _faculty_url() -> str:
    return current_app.config['SUPABASE_FACULTY_URL']


# ─── Leave Requests ────────────────────────────────────────────────

def get_all_leave_requests() -> list:
    """Fetch all leave requests from Supabase with a 30s in-memory cache."""
    now = time.time()
    if _cache['leave_requests']['data'] and (now - _cache['leave_requests']['time'] < CACHE_TTL):
        return _cache['leave_requests']['data']

    try:
        resp = _http_session.get(_leave_url(), headers=_get_headers(), timeout=10)
        if resp.status_code == 401:
            return []
        resp.raise_for_status()
        data = resp.json()
        _cache['leave_requests']['data'] = data if isinstance(data, list) else []
        _cache['leave_requests']['time'] = now
        return _cache['leave_requests']['data']
    except requests.RequestException as e:
        logger.error("Failed to fetch leave requests: %s", e)
        return _cache['leave_requests']['data'] or []


def get_leave_requests_by_email(email: str) -> list:
    """Fetch leave requests for a specific faculty email."""
    try:
        params = {'email': f'eq.{email}'}
        resp = _http_session.get(_leave_url(), headers=_get_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []
    except requests.RequestException as e:
        logger.error("Failed to fetch leave requests for %s: %s", email, e)
        return []


def get_leave_request_by_id(req_id: str) -> Optional[dict]:
    """Fetch a single leave request by its ID."""
    try:
        params = {'id': f'eq.{req_id}'}
        resp = _http_session.get(_leave_url(), headers=_get_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data and isinstance(data, list) and len(data) > 0:
            return data[0]
        return None
    except requests.RequestException as e:
        logger.error("Failed to fetch leave request %s: %s", req_id, e)
        return None


def create_leave_request(payload: dict) -> bool:
    """Insert a new leave request into Supabase."""
    try:
        resp = _http_session.post(
            _leave_url(),
            headers=_get_headers(content_type=True, prefer_minimal=True),
            json=payload,
            timeout=10,
        )
        if resp.status_code < 300:
            logger.info("Leave request created for %s", payload.get('email'))
            return True
        logger.error("Create leave failed: %s - %s", resp.status_code, resp.text)
        return False
    except requests.RequestException as e:
        logger.error("Create leave request exception: %s", e)
        return False


def update_leave_request(req_id: str, update_data: dict) -> bool:
    """Update an existing leave request by ID."""
    try:
        url = f"{_leave_url()}?id=eq.{req_id}"
        resp = _http_session.patch(
            url,
            headers=_get_headers(content_type=True, prefer_minimal=True),
            json=update_data,
            timeout=10,
        )
        if resp.status_code < 300:
            logger.info("Leave request %s updated: %s", req_id, list(update_data.keys()))
            return True
        logger.error("Update leave failed: %s - %s", resp.status_code, resp.text)
        return False
    except requests.RequestException as e:
        logger.error("Update leave request exception: %s", e)
        return False


def get_approved_leave_requests() -> list:
    """Fetch all 'Principal Approved' leave requests with per-request caching."""
    from flask import g
    if 'approved_leave_requests' in g:
        return g.approved_leave_requests

    try:
        params = {'status': 'eq.Principal Approved'}
        resp = _http_session.get(_leave_url(), headers=_get_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        g.approved_leave_requests = data if isinstance(data, list) else []
        return g.approved_leave_requests
    except requests.RequestException as e:
        logger.error("Failed to fetch approved leave requests: %s", e)
        return []


# ─── Faculty Credentials ───────────────────────────────────────────

def get_faculty_by_id(faculty_id: str) -> Optional[dict]:
    """Fetch a faculty record by faculty_id."""
    try:
        params = {'faculty_id': f'eq.{faculty_id}'}
        resp = _http_session.get(_faculty_url(), headers=_get_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data and isinstance(data, list) and len(data) > 0:
            return data[0]
        return None
    except requests.RequestException as e:
        logger.error("Failed to fetch faculty %s: %s", faculty_id, e)
        return None


def get_faculty_by_email(email: str) -> Optional[dict]:
    """Fetch a faculty record by email."""
    try:
        params = {'email': f'eq.{email}'}
        resp = _http_session.get(_faculty_url(), headers=_get_headers(), params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data and isinstance(data, list) and len(data) > 0:
            return data[0]
        return None
    except requests.RequestException as e:
        logger.error("Failed to fetch faculty by email %s: %s", email, e)
        return None


def get_faculty_by_emails(emails: list) -> list:
    """Fetch multiple faculty records by email list (for quota lookups)."""
    if not emails:
        return []
    try:
        email_filter = "(" + ",".join(emails) + ")"
        url = f"{_faculty_url()}?email=in.{email_filter}"
        resp = _http_session.get(url, headers=_get_headers(), timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []
    except requests.RequestException as e:
        logger.error("Failed to fetch faculty by emails: %s", e)
        return []


def get_all_faculty() -> list:
    """Fetch all faculty records with a 30s in-memory cache."""
    now = time.time()
    if _cache['faculty_list']['data'] and (now - _cache['faculty_list']['time'] < CACHE_TTL):
        return _cache['faculty_list']['data']

    try:
        resp = _http_session.get(_faculty_url(), headers=_get_headers(), timeout=10)
        resp.raise_for_status()
        data = resp.json()
        _cache['faculty_list']['data'] = data if isinstance(data, list) else []
        _cache['faculty_list']['time'] = now
        return _cache['faculty_list']['data']
    except requests.RequestException as e:
        logger.error("Failed to fetch faculty list: %s", e)
        return _cache['faculty_list']['data'] or []


def create_faculty(payload: dict) -> bool:
    """Insert a new faculty record."""
    try:
        resp = _http_session.post(
            _faculty_url(),
            headers=_get_headers(content_type=True),
            json=payload,
            timeout=10,
        )
        if resp.status_code in (200, 201, 204):
            logger.info("Faculty created: %s", payload.get('faculty_id'))
            return True
        logger.error("Create faculty failed: %s - %s", resp.status_code, resp.text)
        return False
    except requests.RequestException as e:
        logger.error("Create faculty exception: %s", e)
        return False


def update_faculty(faculty_id: str, update_data: dict) -> bool:
    """Update a faculty record by faculty_id."""
    try:
        url = f"{_faculty_url()}?faculty_id=eq.{faculty_id}"
        resp = _http_session.patch(
            url,
            headers=_get_headers(content_type=True, prefer_minimal=True),
            json=update_data,
            timeout=10,
        )
        if resp.status_code < 300:
            logger.info("Faculty %s updated", faculty_id)
            return True
        logger.error("Update faculty failed: %s - %s", resp.status_code, resp.text)
        return False
    except requests.RequestException as e:
        logger.error("Update faculty exception: %s", e)
        return False


def delete_faculty(faculty_id: str) -> bool:
    """Delete a faculty record by faculty_id."""
    try:
        url = f"{_faculty_url()}?faculty_id=eq.{faculty_id}"
        resp = _http_session.delete(
            url,
            headers=_get_headers(prefer_minimal=True),
            timeout=10,
        )
        if resp.status_code < 300:
            logger.info("Faculty %s deleted", faculty_id)
            return True
        logger.error("Delete faculty failed: %s - %s", resp.status_code, resp.text)
        return False
    except requests.RequestException as e:
        logger.error("Delete faculty exception: %s", e)
        return False
