import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash

# ==========================================
# CONFIGURATION - PLEASE FILL THESE IN
# ==========================================
# Example: https://xyz.supabase.co/rest/v1/leave_requests
SUPABASE_URL = "https://mygsvmoguhettdjwvkfn.supabase.co/rest/v1/leave_requests" 
SUPABASE_FACULTY_URL = "https://mygsvmoguhettdjwvkfn.supabase.co/rest/v1/faculty_credentials"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im15Z3N2bW9ndWhldHRkand2a2ZuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzY1MTQ5MTAsImV4cCI6MjA5MjA5MDkxMH0.C8oG7c24Zwfdjb_Wd1PEQ7g61fSkD6hQtdiK-JynDx8"
EMAIL = "sameekshamjain7801@gmail.com"
PASSWORD = "dfnilrfvfahsnvjw"

app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')
app.secret_key = "leave_flow_secret_key"

# ==========================================
# FACULTY CREDENTIALS DATABASE (IN-MEMORY FALLBACK)
# ==========================================
FACULTY_CREDENTIALS = {}

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
    
    return render_template('login.html')

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
        
    return render_template('dashboard.html', requests=data)

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
    
    return render_template(
        'faculty_submission.html',
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
    
    return render_template('hod_faculty_management.html', faculty_list=faculty_list)

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
