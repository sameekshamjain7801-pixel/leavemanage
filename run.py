"""
Application entry point.
Use this to run the app locally or via Gunicorn.
"""

import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("------------------------------------------")
    print("  LeaveFlow Server Initializing...")
    print(f"  Environment: {os.environ.get('FLASK_ENV', 'development')}")
    print(f"  Access locally at: http://127.0.0.1:{port}")
    print("  Faculty: faculty1-5 (password: pass123)")
    print("  Admin: hod1/admin123 or principal/admin123")
    print("------------------------------------------")
    app.run(debug=app.config.get('DEBUG', True), host='0.0.0.0', port=port)
