import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[Config.RATELIMIT_DEFAULT]
)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    csrf.init_app(app)
    limiter.init_app(app)

    # Ensure required directories exist
    from app.db_init import ensure_directories, migrate_database_schema, seed_reference_data
    ensure_directories(app)

    # Register Blueprints
    from app.routes.auth import bp as auth_bp
    from app.routes.user import bp as user_bp
    from app.routes.officer import bp as officer_bp
    from app.routes.admin import bp as admin_bp
    from app.routes.api import bp as api_bp
    from app.routes.evidence import bp as evidence_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(officer_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(evidence_bp)

    # Database Migration and Initial Seeding
    with app.app_context():
        db.create_all()
        migrate_database_schema(db)
        seed_reference_data(db)

    # Global Context Processors for Navigation & Alerts
    @app.context_processor
    def inject_global_template_vars():
        unread_count = 0
        if current_user.is_authenticated:
            from app.models import Notification
            unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        return {
            'app_name': 'CivicShield AI',
            'app_subtitle': 'Smart Crime Reporting & Complaint Management System',
            'unread_notifications_count': unread_count,
            'districts_list': Config.DISTRICTS,
            'crime_categories_list': Config.CRIME_CATEGORIES,
            'police_stations_list': Config.POLICE_STATIONS
        }

    # Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html', title='Access Forbidden'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html', title='Page Not Found'), 404

    @app.errorhandler(429)
    def ratelimit_error(error):
        return render_template('errors/429.html', title='Too Many Requests', error=error), 429

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html', title='Server Error'), 500

    return app

from app import models
