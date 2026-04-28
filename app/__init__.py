"""
Application factory for LeaveFlow.
Creates and configures the Flask application instance.
"""

import logging
import os
from flask import Flask
from config import get_config


def create_app(config_override=None):
    """
    Application factory.

    Args:
        config_override: Optional config object to override auto-detection.

    Returns:
        Configured Flask application instance.
    """
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
        static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'),
        static_url_path='/static',
    )

    # Load configuration
    config = config_override or get_config()
    app.config.from_object(config)

    # Store config properties as app config for easy access
    app.config['SUPABASE_LEAVE_URL'] = config.SUPABASE_LEAVE_URL
    app.config['SUPABASE_FACULTY_URL'] = config.SUPABASE_FACULTY_URL

    # Configure structured logging
    _setup_logging(app)

    # Register blueprints
    _register_blueprints(app)

    # Register global error handlers
    _register_error_handlers(app)

    # Request logging middleware
    _register_request_hooks(app)

    # Register context processors
    _register_context_processors(app)

    app.logger.info("LeaveFlow application initialized [env=%s]", os.environ.get('FLASK_ENV', 'development'))

    @app.route('/health')
    def health_check():
        return 'OK', 200

    return app


def _setup_logging(app):
    """Configure structured logging for the application."""
    log_level = logging.DEBUG if app.debug else logging.INFO
    handler = logging.StreamHandler()
    handler.setLevel(log_level)
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    handler.setFormatter(formatter)

    # Clear default handlers and add ours
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)

    # Suppress noisy libraries in production
    if not app.debug:
        logging.getLogger('urllib3').setLevel(logging.WARNING)


def _register_blueprints(app):
    """Register all application blueprints."""
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.faculty import faculty_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(faculty_bp)
    app.register_blueprint(admin_bp)


def _register_error_handlers(app):
    """Register global error handlers that return friendly responses."""
    from flask import render_template, jsonify, request

    @app.errorhandler(404)
    def not_found(error):
        if request.accept_mimetypes.best == 'application/json':
            return jsonify({'error': 'Resource not found'}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error("Internal server error: %s", error)
        if request.accept_mimetypes.best == 'application/json':
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden(error):
        if request.accept_mimetypes.best == 'application/json':
            return jsonify({'error': 'Forbidden'}), 403
        return render_template('errors/403.html'), 403


def _register_request_hooks(app):
    """Register before/after request hooks for logging and security headers."""
    from flask import request, g
    import time

    @app.before_request
    def before_request():
        g.request_start_time = time.time()

    @app.after_request
    def after_request(response):
        # Log request duration
        if hasattr(g, 'request_start_time'):
            elapsed = (time.time() - g.request_start_time) * 1000
            app.logger.debug(
                "%s %s %s %.1fms",
                request.method, request.path, response.status_code, elapsed
            )

        # Security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response


def _register_context_processors(app):
    """Register global context processors."""
    @app.context_processor
    def inject_faculty_list():
        """Globally inject faculty list for all administrative roles."""
        from flask import session
        role = session.get('role')
        if role and role != 'faculty':
            from app.services.db_service import get_all_faculty
            try:
                return {'faculty_list': get_all_faculty()}
            except Exception:
                return {'faculty_list': []}
        return {'faculty_list': []}

    @app.context_processor
    def inject_user_avatar():
        from flask import session, current_app
        import os
        
        user_id = session.get('faculty_id') or session.get('role')
        if not user_id:
            return {'user_avatar': None}
            
        avatar_filename = f"{user_id}.jpg"
        static_dir = current_app.static_folder
        avatar_path = os.path.join(static_dir, 'uploads', 'avatars', avatar_filename)
        
        if os.path.exists(avatar_path):
            import time
            v = int(os.path.getmtime(avatar_path))
            return {'user_avatar': f"/static/uploads/avatars/{avatar_filename}?v={v}"}
            
        return {'user_avatar': None}
