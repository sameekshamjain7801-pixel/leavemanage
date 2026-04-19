import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from flask import Flask, render_template_string, request, redirect, url_for, session, flash

# ==========================================
# CONFIGURATION - PLEASE FILL THESE IN
# ==========================================
# Example: https://xyz.supabase.co/rest/v1/leave_requests
SUPABASE_URL = "https://mygsvmoguhettdjwvkfn.supabase.co/rest/v1/leave_requests" 
SUPABASE_FACULTY_URL = "https://mygsvmoguhettdjwvkfn.supabase.co/rest/v1/faculty_credentials"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im15Z3N2bW9ndWhldHRkand2a2ZuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY1MTQ5MTAsImV4cCI6MjA5MjA5MDkxMH0.C8oG7c24Zwfdjb_Wd1PEQ7g61fSkD6hQtdiK-JynDx8"
EMAIL = "sameekshamjain7801@gmail.com"
PASSWORD = "dfnilrfvfahsnvjw"

app = Flask(__name__)
app.secret_key = "leave_flow_secret_key"

# ==========================================
# FACULTY CREDENTIALS DATABASE (IN-MEMORY FALLBACK)
# ==========================================
FACULTY_CREDENTIALS = {}

# ==========================================
# UI TEMPLATES (BOOTSTRAP 5 + CUSTOM CSS)
# ==========================================

BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LeaveFlow | Faculty Leave Management</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css">
    <style>
        :root {
            --primary: #8b5cf6; /* Vibrant Purple */
            --primary-dark: #7c3aed;
            --secondary: #64748b;
            --bg-body: #fdfaff; /* Light purple tint */
            --card-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }
        body {
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-body);
            color: #1e293b;
        }
        .navbar {
            background: white;
            border-bottom: 2px solid #f3e8ff;
            padding: 1rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }
        .navbar-brand { font-weight: 800; font-size: 1.6rem; letter-spacing: -1px; }
        .card {
            border: none;
            border-radius: 20px;
            box-shadow: var(--card-shadow);
            transition: all 0.3s ease;
        }
        .btn { border-radius: 12px; font-weight: 700; padding: 0.75rem 1.5rem; transition: all 0.3s ease; }
        .btn-primary { background: linear-gradient(135deg, var(--primary), var(--primary-dark)); border: none; }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(139, 92, 246, 0.4); }
        .status-badge {
            padding: 0.6rem 1.2rem;
            border-radius: 50px;
            font-size: 0.8rem;
            font-weight: 700;
            text-transform: uppercase;
            display: inline-block;
        }
        .bg-pending { background-color: #fef9c3; color: #854d0e; }
        .bg-hod-approved { background-color: #dcfce7; color: #166534; }
        .bg-principal-approved { background-color: #dbeafe; color: #1e40af; }
        .bg-rejected { background-color: #fee2e2; color: #991b1b; }
        .login-card { max-width: 600px; margin: 3rem auto; padding: 0 1.5rem; }
        .dashboard-header { border-bottom: 2px solid #e2e8f0; padding-bottom: 1.5rem; margin-bottom: 2rem; flex-wrap: wrap; gap: 1rem; }
        textarea.form-control { border-radius: 12px; background-color: #f1f5f9; border: 1px solid #e2e8f0; }
        textarea.form-control:focus { background-color: white; }
        .request-card-actions { display: flex; flex-wrap: wrap; gap: 0.5rem; }
        .request-card-actions .btn { padding: 0.6rem 1rem; font-size: 0.9rem; }
        
        /* Responsive Table */
        .table-responsive { overflow-x: auto; -webkit-overflow-scrolling: touch; }
        .table { margin-bottom: 0; }
        .table th, .table td { vertical-align: middle; white-space: nowrap; }
        
        /* Form Responsive */
        .form-control, .form-select { border-radius: 10px; padding: 0.65rem 0.75rem; font-size: 1rem; }
        .form-control:focus, .form-select:focus { border-color: var(--primary); box-shadow: 0 0 0 0.2rem rgba(139, 92, 246, 0.25); }
        
        /* Modal Responsive */
        .modal-dialog { margin: 0.5rem auto; }
        .modal-content { margin: 0; }
        
        /* Card Responsive */
        .card { margin-bottom: 1.5rem; }
        
        /* Container Padding */
        .container-fluid, .container { padding-left: 0.75rem; padding-right: 0.75rem; }
        
        /* Navbar Responsive */
        .navbar { padding: 0.75rem 0; }
        .navbar-brand { margin: 0 0.5rem; }
        
        @media (max-width: 1200px) {
            .container-fluid, .container { padding-left: 1rem; padding-right: 1rem; }
            h2 { font-size: 1.75rem; }
            h3 { font-size: 1.4rem; }
            h4 { font-size: 1.15rem; }
            .btn { padding: 0.65rem 1.25rem; font-size: 0.95rem; }
            .login-card { max-width: 700px; }
        }
        
        @media (min-width: 1400px) {
            .login-card { max-width: 800px; }
        }
        
        @media (max-width: 992px) {
            .navbar-brand { font-size: 1.4rem; }
            .login-card { max-width: 100%; margin: 2rem 1rem; }
            .dashboard-header { flex-direction: column; align-items: flex-start !important; gap: 1rem; }
            .card { border-radius: 15px; }
            h2 { font-size: 1.6rem; }
            h3 { font-size: 1.3rem; }
            .btn-sm { padding: 0.5rem 0.85rem; font-size: 0.9rem; }
        }
        
        @media (max-width: 768px) {
            .navbar { padding: 0.5rem 0; }
            .navbar-brand { font-size: 1.2rem; margin: 0; }
            .navbar-brand i { display: inline-block; }
            .ms-auto { margin-left: auto !important; }
            .gap-3 { gap: 0.75rem !important; }
            .d-none.d-md-block { display: none !important; }
            
            .login-card { max-width: 100%; margin: 1.5rem 0.75rem; padding: 0; }
            .login-card .card { border-radius: 12px; padding: 1.5rem !important; }
            .login-card h2 { font-size: 1.4rem; }
            
            .dashboard-header { padding-bottom: 1rem; margin-bottom: 1.5rem; }
            .dashboard-header h2 { margin-bottom: 0.5rem; font-size: 1.4rem; }
            
            .card { margin-bottom: 1rem; padding: 1rem !important; }
            .card h4 { font-size: 1.1rem; }
            
            .btn { padding: 0.6rem 1rem; font-size: 0.9rem; }
            .btn-sm { padding: 0.45rem 0.75rem; font-size: 0.85rem; }
            
            /* Table on mobile */
            .table { font-size: 0.9rem; }
            .table thead { font-size: 0.8rem; }
            .table th, .table td { padding: 0.5rem 0.25rem; }
            
            /* Form on mobile */
            .row { margin-right: -0.375rem; margin-left: -0.375rem; }
            .col, [class*="col-"] { padding-right: 0.375rem; padding-left: 0.375rem; }
            .form-control, .form-select { padding: 0.6rem 0.6rem; font-size: 0.95rem; }
            .form-label { font-size: 0.9rem; margin-bottom: 0.35rem; }
            
            /* Modal on mobile */
            .modal-dialog { margin: 0.5rem; }
            .modal-content { border-radius: 12px; }
            .modal-header { padding: 1rem; }
            .modal-body { padding: 1rem; }
            .modal-footer { padding: 1rem; gap: 0.5rem; }
            
            /* Input group on mobile */
            .input-group-text { padding: 0.6rem 0.5rem; font-size: 0.9rem; }
            
            .container-fluid, .container { padding-left: 0.75rem; padding-right: 0.75rem; }
            
            /* Faculty management form */
            .col-12 { width: 100%; }
            .col-md-6 { width: 100%; }
        }
        
        @media (max-width: 576px) {
            .navbar-brand { font-size: 1rem; }
            .navbar-brand i { font-size: 1.2rem; }
            
            .login-card { margin: 1rem 0.5rem; }
            .login-card .card { padding: 1.25rem !important; }
            .login-card h2 { font-size: 1.25rem; }
            .login-card p { font-size: 0.9rem; }
            
            h2 { font-size: 1.3rem !important; }
            h3 { font-size: 1.1rem !important; }
            h4 { font-size: 1rem !important; }
            h5 { font-size: 0.95rem !important; }
            
            .card { margin-bottom: 0.75rem; padding: 0.75rem !important; border-radius: 10px; }
            .card h4 { font-size: 1rem; margin-bottom: 0.75rem; }
            
            .btn { padding: 0.5rem 0.8rem; font-size: 0.85rem; border-radius: 8px; }
            .btn-sm { padding: 0.4rem 0.65rem; font-size: 0.8rem; }
            .btn-lg { padding: 0.75rem 1.5rem; font-size: 0.9rem; }
            
            /* Text sizing */
            .small { font-size: 0.8rem; }
            .text-muted { font-size: 0.85rem; }
            
            /* Table on extra small */
            .table { font-size: 0.8rem; }
            .table thead { font-size: 0.75rem; }
            .table th, .table td { padding: 0.35rem 0.2rem; }
            .table-responsive { margin: 0 -0.75rem; padding: 0 0.75rem; }
            
            /* Form on extra small */
            .form-control, .form-select { padding: 0.5rem 0.5rem; font-size: 0.9rem; }
            .form-label { font-size: 0.85rem; }
            .mb-3 { margin-bottom: 0.75rem !important; }
            .mb-4 { margin-bottom: 1rem !important; }
            
            /* Modal on extra small */
            .modal-dialog { margin: 0.25rem; }
            .modal-content { border-radius: 10px; }
            .modal-header { padding: 0.75rem; }
            .modal-body { padding: 0.75rem; }
            .modal-footer { padding: 0.75rem; gap: 0.25rem; }
            
            .container-fluid, .container { padding-left: 0.5rem; padding-right: 0.5rem; }
            
            .py-4 { padding-top: 1rem !important; padding-bottom: 1rem !important; }
            .py-5 { padding-top: 1.5rem !important; padding-bottom: 1.5rem !important; }
            
            .pt-0 { padding-top: 0 !important; }
            .p-4 { padding: 0.75rem !important; }
            
            /* Gap utilities */
            .gap-2 { gap: 0.35rem !important; }
            .gap-3 { gap: 0.5rem !important; }
            
            .me-2 { margin-right: 0.35rem !important; }
            .ms-auto { margin-left: auto !important; }
            .me-auto { margin-right: auto !important; }
            
            /* Badges responsive */
            .badge { padding: 0.35rem 0.6rem; font-size: 0.75rem; }
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-light bg-white border-bottom border-light">
        <div class="container-fluid">
            <a class="navbar-brand text-primary fw-bold" href="/"><i class="bi bi-airplane-engines-fill me-2"></i><span class="d-none d-sm-inline">LeaveFlow</span></a>
            {% if session.get('role') %}
            <div class="ms-auto d-flex align-items-center gap-2 gap-md-3 flex-wrap">
                <div class="d-none d-md-block text-end border-end border-light pe-3">
                    <div class="small text-muted">Signed in as</div>
                    <div class="fw-bold text-uppercase small">
                        {% if session.get('role') == 'faculty' %}
                            <span class="d-none d-lg-inline">{{ session.get('faculty_name', 'Faculty') }}</span>
                            <span class="d-lg-none">Faculty</span>
                        {% else %}
                            {{ session['role'] }}
                        {% endif %}
                    </div>
                </div>
                <a href="{{ url_for('logout') }}" class="btn btn-outline-danger btn-sm"><i class="bi bi-box-arrow-right me-1"></i><span class="d-none d-md-inline">Sign Out</span></a>
            </div>
            {% endif %}
        </div>
    </nav>

    <div class="container-fluid py-3 py-md-4">
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="alert alert-{{ category }} alert-dismissible fade show border-0 shadow-sm" role="alert">
                {{ message }}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}
        
        {% block content %}{% endblock %}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Confirmation before actions
        function confirmAction(action) {
            return confirm("Are you sure you want to " + action + " this request?");
        }
    </script>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<div class="login-card shadow-lg card border-0">
    <div class="card-body p-3 p-md-5">
        <div class="text-center mb-4">
            <h2 class="fw-bold mb-2">Welcome Back</h2>
            <p class="text-muted mb-0 small">Enter your credentials to manage leave requests</p>
        </div>
        
        <!-- Role Selection Tabs -->
        <ul class="nav nav-tabs nav-fill mb-4 gap-1" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active small fw-bold" id="faculty-tab" data-bs-toggle="tab" data-bs-target="#faculty-login" type="button" role="tab">
                    <i class="bi bi-mortarboard me-1"></i><span class="d-none d-sm-inline">Faculty</span>
                </button>
        </li>
        <li class="nav-item" role="presentation">
            <button class="nav-link small fw-bold" id="admin-tab" data-bs-toggle="tab" data-bs-target="#admin-login" type="button" role="tab">
                <i class="bi bi-shield-check me-1"></i><span class="d-none d-sm-inline">Admin</span>
            </button>
        </li>
    </ul>

    <div class="tab-content">
        <!-- Faculty Login -->
        <div class="tab-pane fade show active" id="faculty-login" role="tabpanel">
            <form action="{{ url_for('login') }}" method="POST">
                <input type="hidden" name="role_type" value="faculty">
                <div class="mb-3">
                    <label class="form-label fw-bold mb-2 small">Faculty ID</label>
                    <div class="input-group">
                        <span class="input-group-text bg-light border-0"><i class="bi bi-person"></i></span>
                        <input type="text" name="username" class="form-control bg-light border-0" required placeholder="faculty1, faculty2, etc.">
                    </div>

                </div>
                <div class="mb-4">
                    <label class="form-label fw-bold mb-2 small">Password</label>
                    <div class="input-group">
                        <span class="input-group-text bg-light border-0"><i class="bi bi-lock"></i></span>
                        <input type="password" name="password" class="form-control bg-light border-0" required placeholder="••••••••">
                    </div>

                </div>
                <button type="submit" class="btn btn-primary w-100 py-2 py-md-3 shadow">Sign In</button>
            </form>
        </div>

        <!-- Admin Login -->
        <div class="tab-pane fade" id="admin-login" role="tabpanel">
            <form action="{{ url_for('login') }}" method="POST">
                <input type="hidden" name="role_type" value="admin">
                <div class="mb-3">
                    <label class="form-label fw-bold mb-2 small">Username</label>
                    <div class="input-group">
                        <span class="input-group-text bg-light border-0"><i class="bi bi-person"></i></span>
                        <input type="text" name="username" class="form-control bg-light border-0" required placeholder="hod or principal">
                    </div>
                </div>
                <div class="mb-4">
                    <label class="form-label fw-bold mb-2 small">Password</label>
                    <div class="input-group">
                        <span class="input-group-text bg-light border-0"><i class="bi bi-lock"></i></span>
                        <input type="password" name="password" class="form-control bg-light border-0" required placeholder="••••••••">
                    </div>

                </div>
                <button type="submit" class="btn btn-primary w-100 py-2 py-md-3 shadow">Sign In</button>
            </form>
        </div>
    </div>

    <div class="mt-4 text-center">
        <small class="text-muted">Faculty & Admin Portal | Responsive Leave Management System</small>
    </div>
    </div>
</div>
"""

DASHBOARD_TEMPLATE = """
<div class="dashboard-header d-flex justify-content-between align-items-start mb-3 mb-md-4 flex-wrap">
    <div class="flex-grow-1 mb-2 mb-md-0">
        <h2 class="fw-bold mb-1 text-capitalize">{{ session['role'] }} Dashboard</h2>
        <p class="text-muted mb-0 small">Management Portal for Leave Approvals</p>
    </div>
    <div class="d-flex flex-wrap gap-2 align-items-start ms-auto">
        <span class="badge bg-primary rounded-pill px-2 px-md-3 py-1 py-md-2 text-nowrap">{{ requests|length }} Pending</span>
        {% if session['role'] == 'hod' or session['role'] == 'principal' %}
        <a href="{{ url_for('manage_faculty') }}" class="btn btn-sm btn-outline-success"><i class="bi bi-people-fill me-1"></i><span class="d-none d-md-inline">Manage</span> Faculty</a>
        {% endif %}
    </div>
</div>

{% if not requests %}
<div class="text-center py-5">
    <div class="mb-3"><i class="bi bi-clipboard2-check text-muted" style="font-size: 3rem; opacity: 0.5;"></i></div>
    <h4 class="text-muted">All clear!</h4>
    <p class="text-secondary small">No pending leave requests</p>
</div>
{% endif %}

<div class="row g-2 g-md-4">
    {% for req in requests %}
    <div class="col-12">
        <div class="card p-0 overflow-hidden border-start border-3 border-md-4 {% if 'Approved' in req.status %}border-success{% elif 'Rejected' in req.status %}border-danger{% else %}border-warning{% endif %}">
            <div class="card-body p-3 p-md-4">
                <div class="row align-items-stretch g-0">
                    <div class="col-md-7 request-card-section pb-3 pb-md-4 pe-md-3 border-md-end mb-3 mb-md-0">
                        <div class="d-flex align-items-center mb-2 mb-md-3">
                            <div class="flex-shrink-0 bg-primary bg-opacity-10 text-primary rounded-circle p-2 p-md-3 me-2 me-md-3">
                                <i class="bi bi-person-fill fs-5"></i>
                            </div>
                            <div class="flex-grow-1">
                                <h5 class="fw-bold mb-0 small">{{ req.student_name }}</h5>
                                <div class="text-muted small">{{ req.department }} • {{ req.email }}</div>
                            </div>
                        </div>
                        <div class="mb-2 mb-md-3 d-flex flex-wrap gap-2">
                            <span class="badge bg-light text-dark border small"><i class="bi bi-calendar-event me-1"></i> {{ req.from_date }} → {{ req.to_date }}</span>
                            <span class="status-badge 
                                {% if req.status == 'Pending' %}bg-pending
                                {% elif req.status == 'HOD Approved' %}bg-hod-approved
                                {% elif req.status == 'Principal Approved' %}bg-principal-approved
                                {% else %}bg-rejected{% endif %} small">{{ req.status }}</span>
                        </div>
                        <p class="card-text text-break small"><strong>Reason:</strong> {{ req.reason }}</p>
                        {% if session['role'] == 'hod' %}
                        <button type="button" class="btn btn-outline-secondary btn-sm mt-2"
                            data-bs-toggle="modal" data-bs-target="#editModal"
                            onclick="fillEditModal('{{ req.id }}','{{ req.student_name }}','{{ req.email }}','{{ req.department }}','{{ req.reason }}','{{ req.from_date }}','{{ req.to_date }}')"
                        ><i class="bi bi-pencil-fill me-1"></i> Edit</button>
                        {% endif %}
                    </div>
                    <div class="col-md-5 request-card-section bg-light p-2 p-md-4 rounded-2 mt-3 mt-md-0">
                        <form action="{{ url_for('process_leave') }}" method="POST">
                            <input type="hidden" name="id" value="{{ req.id }}">
                            <div class="mb-2 mb-md-3">
                                <label class="small fw-bold text-uppercase text-secondary mb-1 d-block">Remarks</label>
                                <textarea name="remarks" class="form-control form-control-sm" rows="2" placeholder="Add remarks...">{{ req.hod_remarks if session['role'] == 'hod' else req.principal_remarks or '' }}</textarea>
                            </div>
                            <div class="mb-2 mb-md-3">
                                <label class="small fw-bold text-uppercase text-secondary mb-1 d-block">Email</label>
                                <textarea name="email_body" class="form-control form-control-sm" rows="2" style="font-size: 0.8rem;">Dear {{ req.student_name }},
Your leave: {{ req.from_date }} to {{ req.to_date }} - Status: [PENDING]</textarea>
                            </div>
                            <div class="request-card-actions justify-content-between gap-1">
                                <button type="submit" name="action" value="reject" onclick="return confirmAction('REJECT')" class="btn btn-danger btn-sm flex-fill">Reject</button>
                                <button type="submit" name="action" value="approve" onclick="return confirmAction('APPROVE')" class="btn btn-success btn-sm flex-fill">Approve</button>
                                <button type="submit" name="action" value="send_email" class="btn btn-secondary btn-sm flex-fill"><i class="bi bi-send me-1"></i>Send</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
    {% endfor %}
</div>

<!-- Edit Modal -->
<div class="modal fade" id="editModal" tabindex="-1" aria-labelledby="editModalLabel" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable">
    <div class="modal-content border-0 shadow-lg" style="border-radius:12px;">
      <div class="modal-header border-0 pb-0">
        <h5 class="modal-title fw-bold small" id="editModalLabel"><i class="bi bi-pencil-square me-2 text-primary"></i>Edit Leave Request</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <form action="{{ url_for('edit_leave') }}" method="POST">
        <div class="modal-body p-3 p-md-4">
          <input type="hidden" name="id" id="edit_id">
          <div class="row g-2 g-md-3">
            <div class="col-12 col-md-6">
              <label class="form-label fw-bold small text-uppercase text-secondary mb-2 d-block">Faculty Name</label>
              <input type="text" name="student_name" id="edit_name" class="form-control form-control-sm" required>
            </div>
            <div class="col-12 col-md-6">
              <label class="form-label fw-bold small text-uppercase text-secondary mb-2 d-block">Email</label>
              <input type="email" name="email" id="edit_email" class="form-control form-control-sm" required>
            </div>
            <div class="col-12 col-md-6">
              <label class="form-label fw-bold small text-uppercase text-secondary mb-2 d-block">Department</label>
              <select name="department" id="edit_department" class="form-select form-select-sm" required>
                <option value="">-- Select --</option>
                <option value="Computer Science">Computer Science</option>
                <option value="Information Technology">Information Technology</option>
                <option value="Electronics & Communication">Electronics & Communication</option>
                <option value="Electrical Engineering">Electrical Engineering</option>
                <option value="Mechanical Engineering">Mechanical Engineering</option>
                <option value="Civil Engineering">Civil Engineering</option>
                <option value="Mathematics">Mathematics</option>
                <option value="Physics">Physics</option>
                <option value="Chemistry">Chemistry</option>
                <option value="English">English</option>
                <option value="Management Studies">Management Studies</option>
                <option value="Other">Other</option>
              </select>
            </div>
            <div class="col-12 col-md-6">
              <label class="form-label fw-bold small text-uppercase text-secondary mb-2 d-block">Reason</label>
              <input type="text" name="reason" id="edit_reason" class="form-control form-control-sm" required>
            </div>
            <div class="col-12 col-md-6">
              <label class="form-label fw-bold small text-uppercase text-secondary mb-2 d-block">From Date</label>
              <input type="date" name="from_date" id="edit_from_date" class="form-control form-control-sm" required>
            </div>
            <div class="col-12 col-md-6">
              <label class="form-label fw-bold small text-uppercase text-secondary mb-2 d-block">To Date</label>
              <input type="date" name="to_date" id="edit_to_date" class="form-control form-control-sm" required>
            </div>
          </div>
        </div>
        <div class="modal-footer border-0 gap-2">
          <button type="button" class="btn btn-outline-secondary btn-sm" data-bs-dismiss="modal">Cancel</button>
          <button type="submit" class="btn btn-primary btn-sm"><i class="bi bi-check-lg me-1"></i> Save</button>
        </div>
      </form>
    </div>
  </div>
</div>

<script>
function fillEditModal(id, name, email, dept, reason, from_date, to_date) {
    document.getElementById('edit_id').value = id;
    document.getElementById('edit_name').value = name;
    document.getElementById('edit_email').value = email;
    document.getElementById('edit_department').value = dept;
    document.getElementById('edit_reason').value = reason;
    document.getElementById('edit_from_date').value = from_date;
    document.getElementById('edit_to_date').value = to_date;
}
</script>
"""

FACULTY_SUBMISSION_TEMPLATE = """
<div class="mb-3 mb-md-4">
    <h2 class="fw-bold mb-1">Submit Leave Request</h2>
    <p class="text-muted small">Fill in the details below to submit your leave request for approval</p>
</div>

<div class="row g-2 g-md-4">
    <div class="col-lg-8">
        <div class="card p-3 p-md-4 border-0 shadow">
            <form action="{{ url_for('submit_leave') }}" method="POST">
                <div class="row g-2 g-md-3 mb-3 mb-md-4">
                    <div class="col-12 col-md-6">
                        <label class="form-label fw-bold mb-2 small">Full Name</label>
                        <input type="text" name="student_name" class="form-control form-control-sm" value="{{ faculty_name }}" readonly required>
                    </div>
                    <div class="col-12 col-md-6">
                        <label class="form-label fw-bold mb-2 small">Email</label>
                        <input type="email" name="email" class="form-control form-control-sm" value="{{ faculty_email }}" readonly required>
                    </div>
                    <div class="col-12 col-md-6">
                        <label class="form-label fw-bold mb-2 small">Department</label>
                        <input type="text" name="department" class="form-control form-control-sm" value="{{ faculty_department }}" readonly required>
                    </div>
                    <div class="col-12 col-md-6">
                        <label class="form-label fw-bold mb-2 small">Reason for Leave</label>
                        <input type="text" name="reason" class="form-control form-control-sm" placeholder="Medical, Personal, Research, etc." required>
                    </div>
                    <div class="col-12 col-md-6">
                        <label class="form-label fw-bold mb-2 small">From Date</label>
                        <input type="date" name="from_date" class="form-control form-control-sm" required>
                    </div>
                    <div class="col-12 col-md-6">
                        <label class="form-label fw-bold mb-2 small">To Date</label>
                        <input type="date" name="to_date" class="form-control form-control-sm" required>
                    </div>
                </div>
                <div class="d-flex gap-2 justify-content-end flex-wrap">
                    <a href="{{ url_for('logout') }}" class="btn btn-outline-secondary btn-sm">Sign Out</a>
                    <button type="submit" class="btn btn-primary btn-sm"><i class="bi bi-send-fill me-1"></i> Submit</button>
                </div>
            </form>
        </div>
    </div>

    <div class="col-lg-4">
        <div class="card p-3 p-md-4 border-0 shadow bg-primary bg-opacity-10">
            <h5 class="fw-bold mb-3 text-primary"><i class="bi bi-info-circle me-2"></i>Information</h5>
            <ul class="list-unstyled small">
                <li class="mb-2"><i class="bi bi-check-circle text-success me-2"></i> Your request will be reviewed by HOD first</li>
                <li class="mb-2"><i class="bi bi-check-circle text-success me-2"></i> HOD will forward to Principal for final approval</li>
                <li class="mb-2"><i class="bi bi-check-circle text-success me-2"></i> You'll receive email notifications at each step</li>
                <li><i class="bi bi-check-circle text-success me-2"></i> Status: <strong>Pending</strong></li>
            </ul>
        </div>
    </div>
</div>

<!-- My Requests -->
<div class="mt-5">
    <h3 class="fw-bold mb-3">My Leave Requests</h3>
    {% if my_requests %}
    <div class="row g-3">
        {% for req in my_requests %}
        <div class="col-12">
            <div class="card p-0 overflow-hidden border-start border-4 
                {% if req.status == 'Pending' %}border-warning
                {% elif 'Approved' in req.status %}border-success
                {% elif 'Rejected' in req.status %}border-danger
                {% endif %}">
                <div class="card-body p-4">
                    <div class="row align-items-center">
                        <div class="col-md-8">
                            <div class="mb-2">
                                <span class="badge bg-light text-dark border me-2"><i class="bi bi-calendar-event me-1"></i> {{ req.from_date }} to {{ req.to_date }}</span>
                                <span class="status-badge 
                                    {% if req.status == 'Pending' %}bg-pending
                                    {% elif req.status == 'HOD Approved' %}bg-hod-approved
                                    {% elif req.status == 'Principal Approved' %}bg-principal-approved
                                    {% else %}bg-rejected{% endif %}">{{ req.status }}</span>
                            </div>
                            <p class="mb-1"><strong>Reason:</strong> {{ req.reason }}</p>
                            <small class="text-muted">Submitted on: {{ req.created_at }}</small>
                        </div>
                        <div class="col-md-4 text-end">
                            {% if req.hod_remarks %}
                            <div class="mb-2">
                                <small class="text-muted"><strong>HOD Remarks:</strong></small>
                                <p class="mb-0 text-break">{{ req.hod_remarks }}</p>
                            </div>
                            {% endif %}
                            {% if req.principal_remarks and req.status != 'HOD Approved' %}
                            <div>
                                <small class="text-muted"><strong>Principal Remarks:</strong></small>
                                <p class="mb-0 text-break">{{ req.principal_remarks }}</p>
                            </div>
                            {% endif %}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <div class="text-center py-5 card border-0 bg-light">
        <i class="bi bi-inbox text-muted" style="font-size: 3rem;"></i>
        <p class="text-muted mt-3">No leave requests submitted yet</p>
    </div>
    {% endif %}
</div>
"""

HOD_FACULTY_MANAGEMENT_TEMPLATE = """
<div class="mb-4">
    <div class="d-flex flex-column flex-md-row justify-content-between align-items-start align-md-center mb-3 mb-md-4 gap-2 gap-md-0">
        <div>
            <h2 class="fw-bold mb-1">Faculty Management</h2>
            <p class="text-muted mb-0 small">Manage faculty credentials and registrations</p>
        </div>
        <a href="{{ url_for('dashboard') }}" class="btn btn-outline-primary btn-sm mt-2 mt-md-0"><i class="bi bi-arrow-left me-1"></i> Back</a>
    </div>
</div>

{% if session['role'] == 'hod' or session['role'] == 'principal' %}
<!-- Add Faculty Form (HOD & Principal) -->
<div class="card p-3 p-md-4 border-0 shadow mb-4">
    <h4 class="fw-bold mb-3 mb-md-4"><i class="bi bi-person-plus-fill me-2 text-success"></i>Add New Faculty</h4>
    <form action="{{ url_for('create_faculty') }}" method="POST">
        <div class="row g-2 g-md-3">
            <div class="col-12 col-sm-6">
                <label class="form-label fw-bold mb-2 small">Faculty ID</label>
                <input type="text" name="faculty_id" class="form-control" placeholder="e.g. faculty6" required>
                <small class="text-muted d-block mt-1">Unique identifier</small>
            </div>
            <div class="col-12 col-sm-6">
                <label class="form-label fw-bold mb-2 small">Full Name</label>
                <input type="text" name="name" class="form-control" placeholder="Dr. John Smith" required>
            </div>
            <div class="col-12 col-sm-6">
                <label class="form-label fw-bold mb-2 small">Email Address</label>
                <input type="email" name="email" class="form-control" placeholder="faculty@college.edu" required>
            </div>
            <div class="col-12 col-sm-6">
                <label class="form-label fw-bold mb-2 small">Department</label>
                <select name="department" class="form-select" required>
                    <option value="" disabled selected>-- Select --</option>
                    <option value="Computer Science">Computer Science</option>
                    <option value="Information Technology">IT</option>
                    <option value="Electronics & Communication">E&C</option>
                    <option value="Electrical Engineering">Electrical</option>
                    <option value="Mechanical Engineering">Mechanical</option>
                    <option value="Civil Engineering">Civil</option>
                    <option value="Mathematics">Mathematics</option>
                    <option value="Physics">Physics</option>
                    <option value="Chemistry">Chemistry</option>
                    <option value="English">English</option>
                    <option value="Management Studies">Management</option>
                    <option value="Other">Other</option>
                </select>
            </div>
            <div class="col-12 col-sm-6">
                <label class="form-label fw-bold mb-2 small">Password</label>
                <input type="password" name="password" class="form-control" placeholder="Min 6 chars" required minlength="6">
            </div>
            <div class="col-12 col-sm-6">
                <label class="form-label fw-bold mb-2 small">Confirm Password</label>
                <input type="password" name="confirm_password" class="form-control" placeholder="Confirm" required minlength="6">
            </div>
        </div>
        <div class="mt-3 mt-md-4 d-flex gap-2 justify-content-end flex-wrap">
            <button type="reset" class="btn btn-outline-secondary btn-sm">Clear</button>
            <button type="submit" class="btn btn-success btn-sm"><i class="bi bi-check-circle me-1"></i> Create</button>
        </div>
    </form>
</div>
{% endif %}

<!-- Faculty List -->
<div class="card p-3 p-md-4 border-0 shadow">
    <h4 class="fw-bold mb-3 mb-md-4"><i class="bi bi-people-fill me-2 text-primary"></i>Registered Faculty <span class="badge bg-secondary">{{ faculty_list|length }}</span></h4>
    
    {% if faculty_list %}
    <div class="table-responsive">
        <table class="table table-hover border table-sm">
            <thead class="table-light">
                <tr>
                    <th class="text-nowrap">Faculty ID</th>
                    <th class="text-nowrap">Name</th>
                    <th class="text-nowrap">Email</th>
                    <th class="text-nowrap d-none d-lg-table-cell">Department</th>
                    <th class="text-center text-nowrap">Status</th>
                    {% if session['role'] == 'hod' or session['role'] == 'principal' %}<th class="text-center text-nowrap">Actions</th>{% endif %}
                </tr>
            </thead>
            <tbody>
                {% for fac in faculty_list %}
                <tr>
                    <td class="text-nowrap"><strong>{{ fac.faculty_id }}</strong></td>
                    <td class="text-nowrap">{{ fac.name }}</td>
                    <td class="text-nowrap"><small>{{ fac.email }}</small></td>
                    <td class="text-nowrap d-none d-lg-table-cell"><span class="badge bg-light text-dark">{{ fac.department }}</span></td>
                    <td class="text-center text-nowrap"><span class="badge bg-success">Active</span></td>
                    {% if session['role'] == 'hod' or session['role'] == 'principal' %}
                    <td class="text-center text-nowrap">
                        <button type="button" class="btn btn-sm btn-outline-primary" 
                            data-bs-toggle="modal" data-bs-target="#editFacultyModal"
                            onclick="fillEditFacultyModal('{{ fac.faculty_id }}', '{{ fac.name }}', '{{ fac.email }}', '{{ fac.department }}')"
                            title="Edit">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <a href="{{ url_for('delete_faculty', faculty_id=fac.faculty_id) }}" 
                            class="btn btn-sm btn-outline-danger"
                            onclick="return confirm('Delete this faculty?');"
                            title="Delete">
                            <i class="bi bi-trash"></i>
                        </a>
                    </td>
                    {% endif %}
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% else %}
    <div class="text-center py-5">
        <i class="bi bi-inbox text-muted" style="font-size: 3rem;"></i>
        <p class="text-muted mt-3">No faculty registered yet</p>
    </div>
    {% endif %}
</div>

{% if session['role'] == 'hod' or session['role'] == 'principal' %}
<!-- Edit Faculty Modal -->
<div class="modal fade" id="editFacultyModal" tabindex="-1">
  <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable">
    <div class="modal-content border-0 shadow-lg" style="border-radius:12px;">
      <div class="modal-header border-0">
        <h5 class="modal-title fw-bold"><i class="bi bi-pencil-square me-2 text-primary"></i>Edit Faculty</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
      </div>
      <form action="{{ url_for('update_faculty') }}" method="POST">
        <div class="modal-body p-3 p-md-4">
          <input type="hidden" name="faculty_id" id="edit_faculty_id_hidden">
          <div class="mb-3">
            <label class="form-label fw-bold mb-2 small">Faculty ID</label>
            <input type="text" name="faculty_id_display" id="edit_faculty_id_input" class="form-control" readonly>
          </div>
          <div class="mb-3">
            <label class="form-label fw-bold mb-2 small">Full Name</label>
            <input type="text" name="name" id="edit_faculty_name" class="form-control" required>
          </div>
          <div class="mb-3">
            <label class="form-label fw-bold mb-2 small">Email</label>
            <input type="email" name="email" id="edit_faculty_email" class="form-control" required>
          </div>
          <div class="mb-0">
            <label class="form-label fw-bold mb-2 small">Department</label>
            <select name="department" id="edit_faculty_dept" class="form-select" required>
                <option value="Computer Science">Computer Science</option>
                <option value="Information Technology">Information Technology</option>
                <option value="Electronics & Communication">Electronics & Communication</option>
                <option value="Electrical Engineering">Electrical Engineering</option>
                <option value="Mechanical Engineering">Mechanical Engineering</option>
                <option value="Civil Engineering">Civil Engineering</option>
                <option value="Mathematics">Mathematics</option>
                <option value="Physics">Physics</option>
                <option value="Chemistry">Chemistry</option>
                <option value="English">English</option>
                <option value="Management Studies">Management Studies</option>
                <option value="Other">Other</option>
            </select>
          </div>
        </div>
        <div class="modal-footer border-0 gap-2">
          <button type="button" class="btn btn-outline-secondary btn-sm" data-bs-dismiss="modal">Cancel</button>
          <button type="submit" class="btn btn-primary btn-sm"><i class="bi bi-check-lg me-1"></i> Update</button>
        </div>
      </form>
    </div>
  </div>
</div>

<script>
function fillEditFacultyModal(faculty_id, name, email, dept) {
    document.getElementById('edit_faculty_id_hidden').value = faculty_id;
    document.getElementById('edit_faculty_id_input').value = faculty_id;
    document.getElementById('edit_faculty_name').value = name;
    document.getElementById('edit_faculty_email').value = email;
    document.getElementById('edit_faculty_dept').value = dept;
}
</script>
{% endif %}
"""

def wrap_template(child_content):
    return BASE_TEMPLATE.replace("{% block content %}{% endblock %}", child_content)

# ==========================================
# FLASK ROUTES
# ==========================================

@app.route('/')
def index():
    if 'role' in session:
        if session['role'] == 'faculty':
            return redirect(url_for('faculty_dashboard'))
        else:
            return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password')
        role_type = request.form.get('role_type', 'admin')
        
        # Faculty Login
        if role_type == 'faculty':
            # Try Supabase first
            headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
            try:
                params = {"faculty_id": f"eq.{username}"}
                response = requests.get(SUPABASE_FACULTY_URL, headers=headers, params=params)
                if response.status_code == 200:
                    faculty_data = response.json()
                    if faculty_data and len(faculty_data) > 0 and faculty_data[0]['password'] == password:
                        fac = faculty_data[0]
                        session['role'] = 'faculty'
                        session['faculty_id'] = username
                        session['faculty_name'] = fac['name']
                        session['faculty_email'] = fac['email']
                        session['faculty_department'] = fac['department']
                        flash(f"Logged in successfully as {fac['name']}", "success")
                        return redirect(url_for('faculty_dashboard'))
            except:
                pass
            
            # Fallback to local credentials
            if username in FACULTY_CREDENTIALS and FACULTY_CREDENTIALS[username]['password'] == password:
                session['role'] = 'faculty'
                session['faculty_id'] = username
                session['faculty_name'] = FACULTY_CREDENTIALS[username]['name']
                session['faculty_email'] = FACULTY_CREDENTIALS[username]['email']
                session['faculty_department'] = FACULTY_CREDENTIALS[username]['department']
                flash(f"Logged in successfully as {FACULTY_CREDENTIALS[username]['name']}", "success")
                return redirect(url_for('faculty_dashboard'))
            
            flash("Invalid Faculty ID or password. Please try again.", "danger")
        
        # Admin Login (HOD/Principal)
        else:
            # Accept both 'principal' and 'principle' spellings
            if username in ('principal', 'principle'):
                username = 'principal'
            if (username == 'hod' and password == 'admin123') or (username == 'principal' and password == 'admin123'):
                session['role'] = username
                flash(f"Logged in successfully as {username.upper()}", "success")
                return redirect(url_for('dashboard'))
            flash("Invalid username or password. Please try again.", "danger")
    
    return render_template_string(wrap_template(LOGIN_TEMPLATE))

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'role' not in session:
        return redirect(url_for('login'))
    
    role = session['role']
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    
    # Filter based on role as per requirements
    if role == 'hod':
        params = {"status": "eq.Pending"}
    elif role == 'principal':
        params = {"status": "eq.HOD Approved"}
    else:
        return redirect(url_for('logout'))
        
    try:
        response = requests.get(SUPABASE_URL, headers=headers, params=params)
        if response.status_code == 401:
            flash("Database Error: Access denied by Supabase. Please ensure Row Level Security (RLS) is disabled.", "danger")
            data = []
        else:
            data = response.json()
            if not isinstance(data, list): data = []
    except Exception as e:
        flash(f"System Error: {str(e)}", "danger")
        data = []
        
    return render_template_string(wrap_template(DASHBOARD_TEMPLATE), requests=data)

@app.route('/process_leave', methods=['POST'])
def process_leave():
    if 'role' not in session:
        return redirect(url_for('login'))
    
    req_id = request.form.get('id')
    action = request.form.get('action')
    remarks = request.form.get('remarks')
    email_body = request.form.get('email_body')
    role = session['role']
    
    headers = {
        "apikey": SUPABASE_KEY, 
        "Authorization": f"Bearer {SUPABASE_KEY}", 
        "Content-Type": "application/json", 
        "Prefer": "return=minimal"
    }

    # Handle Manual Email Trigger
    if action == 'send_email':
        success = send_manual_email(req_id, email_body)
        if success:
            flash("Professional email dispatched successfully!", "success")
        else:
            flash("Email delivery failed. Please check SMTP configuration.", "danger")
        return redirect(url_for('dashboard'))

    # Handle Approval/Rejection
    new_status = ""
    update_data = {}
    
    if role == 'hod':
        new_status = "HOD Approved" if action == 'approve' else "Rejected"
        update_data = {"status": new_status, "hod_remarks": remarks, "hod_email_body": email_body}
    else:
        new_status = "Principal Approved" if action == 'approve' else "Rejected"
        update_data = {"status": new_status, "principal_remarks": remarks, "principal_email_body": email_body}
        
    try:
        update_url = f"{SUPABASE_URL}?id=eq.{req_id}"
        resp = requests.patch(update_url, headers=headers, json=update_data)
        if resp.status_code < 300:
            flash(f"Request {new_status} successfully!", "success")
            flash("Note: Remember to click 'Send Email' if you want to notify the faculty.", "info")
        elif resp.status_code == 401:
            flash("Database Error: Permission Denied. Check if RLS is enabled on Supabase.", "danger")
        else:
            flash(f"Supabase Error: {resp.status_code} - {resp.text}", "danger")
    except Exception as e:
        flash(f"System Exception: {str(e)}", "danger")
        
    return redirect(url_for('dashboard'))

@app.route('/edit_leave', methods=['POST'])
def edit_leave():
    if 'role' not in session:
        return redirect(url_for('login'))

    req_id = request.form.get('id')
    update_data = {
        "student_name": request.form.get('student_name'),
        "email": request.form.get('email'),
        "department": request.form.get('department'),
        "reason": request.form.get('reason'),
        "from_date": request.form.get('from_date'),
        "to_date": request.form.get('to_date'),
    }

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

    try:
        resp = requests.patch(f"{SUPABASE_URL}?id=eq.{req_id}", headers=headers, json=update_data)
        if resp.status_code < 300:
            flash("Leave request updated successfully!", "success")
        else:
            flash(f"Update failed: {resp.status_code} - {resp.text}", "danger")
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")

    return redirect(url_for('dashboard'))

def send_manual_email(req_id, body):
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    try:
        # Fetch latest data to get email
        resp = requests.get(f"{SUPABASE_URL}?id=eq.{req_id}", headers=headers)
        user_data = resp.json()[0]
        receiver_email = user_data['email']
        
        msg = MIMEMultipart()
        msg['From'] = f"LeaveFlow - Leave Management System <{EMAIL}>"
        msg['To'] = receiver_email
        msg['Subject'] = f"Leave Request Update - {user_data['student_name']}"
        
        # Inject status into body if it's there
        final_body = body.replace("[WILL BE UPDATED ON ACTION]", user_data['status'])
        msg.attach(MIMEText(final_body, 'plain'))
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL, PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"SMTP Critical Error: {e}")
        return False

# ==========================================
# FACULTY ROUTES
# ==========================================

@app.route('/faculty_dashboard')
def faculty_dashboard():
    if 'role' not in session or session['role'] != 'faculty':
        return redirect(url_for('login'))
    
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    faculty_email = session.get('faculty_email')
    
    try:
        # Fetch all requests by this faculty
        params = {"email": f"eq.{faculty_email}"}
        response = requests.get(SUPABASE_URL, headers=headers, params=params)
        if response.status_code == 200:
            my_requests = response.json()
            if not isinstance(my_requests, list):
                my_requests = []
        else:
            my_requests = []
            flash("Could not fetch your requests.", "warning")
    except Exception as e:
        flash(f"Error fetching requests: {str(e)}", "danger")
        my_requests = []
    
    return render_template_string(
        wrap_template(FACULTY_SUBMISSION_TEMPLATE),
        faculty_name=session.get('faculty_name'),
        faculty_email=session.get('faculty_email'),
        faculty_department=session.get('faculty_department'),
        my_requests=my_requests
    )

@app.route('/submit_leave', methods=['POST'])
def submit_leave():
    if 'role' not in session or session['role'] != 'faculty':
        return redirect(url_for('login'))
    
    student_name = request.form.get('student_name')
    email = request.form.get('email')
    department = request.form.get('department')
    reason = request.form.get('reason')
    from_date = request.form.get('from_date')
    to_date = request.form.get('to_date')
    
    # Prepare payload for Supabase
    payload = {
        "student_name": student_name,
        "email": email,
        "department": department,
        "reason": reason,
        "from_date": from_date,
        "to_date": to_date,
        "status": "Pending"
    }
    
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    
    try:
        resp = requests.post(SUPABASE_URL, headers=headers, json=payload)
        if resp.status_code < 300:
            flash("Leave request submitted successfully! Awaiting HOD review.", "success")
        else:
            flash(f"Submission failed: {resp.status_code}", "danger")
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
    
    return redirect(url_for('faculty_dashboard'))

# ==========================================
# HOD/PRINCIPAL FACULTY MANAGEMENT ROUTES
# ==========================================

@app.route('/manage_faculty')
def manage_faculty():
    if 'role' not in session or session['role'] not in ['hod', 'principal']:
        flash("Access Denied.", "danger")
        return redirect(url_for('dashboard'))
    
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    
    faculty_list = []
    
    # Try to get from Supabase
    try:
        response = requests.get(SUPABASE_FACULTY_URL, headers=headers, timeout=5)
        if response.status_code == 200:
            supabase_faculty = response.json()
            if isinstance(supabase_faculty, list) and len(supabase_faculty) > 0:
                faculty_list = supabase_faculty
                print(f"[MANAGE FACULTY] Loaded {len(faculty_list)} faculty from Supabase")
    except Exception as e:
        print(f"[MANAGE FACULTY] Supabase error: {str(e)}")
    
    # If empty, use local credentials
    if not faculty_list:
        faculty_list = [{"id": i, "faculty_id": fid, **fac} for i, (fid, fac) in enumerate(FACULTY_CREDENTIALS.items())]
        if len(FACULTY_CREDENTIALS) > 0:
            print(f"[MANAGE FACULTY] Loaded {len(faculty_list)} faculty from local storage")
    
    return render_template_string(wrap_template(HOD_FACULTY_MANAGEMENT_TEMPLATE), faculty_list=faculty_list)

@app.route('/create_faculty', methods=['POST'])
def create_faculty():
    if 'role' not in session or session['role'] not in ['hod', 'principal']:
        flash("Access Denied.", "danger")
        return redirect(url_for('dashboard'))
    
    faculty_id = request.form.get('faculty_id', '').strip().lower()
    name = request.form.get('name')
    email = request.form.get('email')
    department = request.form.get('department')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    
    # Validation
    if not all([faculty_id, name, email, department, password]):
        flash("All fields are required.", "danger")
        return redirect(url_for('manage_faculty'))
    
    if password != confirm_password:
        flash("Passwords do not match.", "danger")
        return redirect(url_for('manage_faculty'))
    
    if len(password) < 6:
        flash("Password must be at least 6 characters.", "danger")
        return redirect(url_for('manage_faculty'))
    
    # Validation for duplicate faculty ID
    if faculty_id in FACULTY_CREDENTIALS:
        flash(f"Faculty ID '{faculty_id}' already exists.", "danger")
        return redirect(url_for('manage_faculty'))
    
    # Always add to local credentials first (primary storage)
    FACULTY_CREDENTIALS[faculty_id] = {"password": password, "name": name, "email": email, "department": department}
    
    # Try to also create in Supabase
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "faculty_id": faculty_id,
        "name": name,
        "email": email,
        "department": department,
        "password": password
    }
    
    supabase_success = False
    try:
        resp = requests.post(SUPABASE_FACULTY_URL, headers=headers, json=payload, timeout=10)
        print(f"[CREATE FACULTY] Status: {resp.status_code}, Response: {resp.text}")
        if resp.status_code in [200, 201, 204]:
            supabase_success = True
            print(f"[CREATE FACULTY] Successfully saved to Supabase for {faculty_id}")
        else:
            print(f"[CREATE FACULTY] Supabase Error: {resp.status_code} - {resp.text}")
    except requests.exceptions.Timeout:
        print(f"[CREATE FACULTY] Supabase timeout for {faculty_id}")
    except Exception as supabase_error:
        print(f"[CREATE FACULTY] Supabase exception: {str(supabase_error)}")
    
    try:
        # Send welcome email to faculty
        send_faculty_registration_email(name, email, faculty_id, password)
    except Exception as email_error:
        print(f"[CREATE FACULTY] Email error: {str(email_error)}")
    
    msg = f"Faculty '{name}' created successfully!"
    if supabase_success:
        msg += " ✓ Saved to Supabase."
    else:
        msg += " (Stored locally)"
    msg += f" Email sent to {email}"
    flash(msg, "success")
    
    return redirect(url_for('manage_faculty'))

@app.route('/update_faculty', methods=['POST'])
def update_faculty():
    if 'role' not in session or session['role'] not in ['hod', 'principal']:
        flash("Access Denied.", "danger")
        return redirect(url_for('dashboard'))
    
    try:
        faculty_id = request.form.get('faculty_id')
        name = request.form.get('name')
        email = request.form.get('email')
        department = request.form.get('department')
        
        # Validation
        if not all([faculty_id, name, email, department]):
            flash("All fields are required.", "danger")
            return redirect(url_for('manage_faculty'))
        
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        
        payload = {
            "name": name,
            "email": email,
            "department": department
        }
        
        # Try Supabase first (update by faculty_id)
        try:
            resp = requests.patch(f"{SUPABASE_FACULTY_URL}?faculty_id=eq.{faculty_id}", headers=headers, json=payload, timeout=5)
            if resp.status_code >= 300 and resp.status_code != 404:
                print(f"Supabase update error: {resp.status_code} - {resp.text}")
        except requests.exceptions.Timeout:
            print("Supabase timeout")
        except Exception as supabase_error:
            print(f"Supabase error: {str(supabase_error)}")
        
        # Also update local credentials
        if faculty_id in FACULTY_CREDENTIALS:
            FACULTY_CREDENTIALS[faculty_id]['name'] = name
            FACULTY_CREDENTIALS[faculty_id]['email'] = email
            FACULTY_CREDENTIALS[faculty_id]['department'] = department
        
        flash("Faculty information updated successfully!", "success")
        return redirect(url_for('manage_faculty'))
        
    except Exception as e:
        print(f"Update error: {str(e)}")
        flash(f"Update error: {str(e)}", "danger")
        return redirect(url_for('manage_faculty'))

@app.route('/delete_faculty/<faculty_id>')
def delete_faculty(faculty_id):
    if 'role' not in session or session['role'] not in ['hod', 'principal']:
        flash("Access Denied.", "danger")
        return redirect(url_for('dashboard'))
    
    try:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Prefer": "return=minimal"
        }
        
        # Try Supabase first
        try:
            resp = requests.delete(f"{SUPABASE_FACULTY_URL}?id=eq.{faculty_id}", headers=headers, timeout=5)
            if resp.status_code >= 300 and resp.status_code != 404:
                print(f"Supabase delete error: {resp.status_code} - {resp.text}")
        except requests.exceptions.Timeout:
            print("Supabase delete timeout")
        except Exception as supabase_error:
            print(f"Supabase delete error: {str(supabase_error)}")
        
        # Also try to remove from local credentials if faculty_id is a key
        removed_local = False
        for fid in list(FACULTY_CREDENTIALS.keys()):
            if str(faculty_id).lower() in str(fid).lower() or str(faculty_id) == fid:
                del FACULTY_CREDENTIALS[fid]
                removed_local = True
                break
        
        if removed_local:
            flash("Faculty deleted successfully!", "success")
        else:
            flash("Faculty deleted from system!", "success")
            
    except Exception as e:
        print(f"Delete error: {str(e)}")
        flash(f"Delete error: {str(e)}", "danger")
    
    return redirect(url_for('manage_faculty'))

def send_faculty_registration_email(name, email, faculty_id, password):
    """Send registration email to newly created faculty"""
    try:
        msg = MIMEMultipart()
        msg['From'] = f"LeaveFlow - Leave Management System <{EMAIL}>"
        msg['To'] = email
        msg['Subject'] = "Welcome to LeaveFlow - Your Faculty Account"
        
        body = f"""Dear {name},

Welcome to LeaveFlow - Faculty Leave Management System!

Your account has been created by the HOD. Here are your login credentials:

Faculty ID: {faculty_id}
Password: {password}
URL: http://127.0.0.1:5000

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
        
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL, PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Error sending registration email: {e}")
        return False

# ==========================================
# MAIN EXECUTION
# ==========================================

if __name__ == '__main__':
    print("------------------------------------------")
    print("LeaveFlow Server Initializing...")
    print("Access locally at: http://127.0.0.1:5000")
    print("Faculty Credentials: faculty1-5 (password: pass123)")
    print("Admin Credentials: hod/admin123 or principal/admin123")
    print("------------------------------------------")
    app.run(debug=True, port=5000)
