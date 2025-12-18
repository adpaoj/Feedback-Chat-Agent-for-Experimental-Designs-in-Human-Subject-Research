"""
ChatAI Integration

Flask-based web application for AI-powered chat interactions.
"""

from flask import Flask, jsonify
from config import Config
from app.extensions import db, login_manager, sess, migrate
import logging

def create_app(config_class=Config):
    """
    Application factory function to create and configure the Flask app.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    sess.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    # Register CLI commands
    from app.commands import init_db_command, check_capabilities_command
    app.cli.add_command(init_db_command)
    app.cli.add_command(check_capabilities_command)

    # User loader
    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Error handlers
    @app.errorhandler(500)
    def internal_error(e):
        """Handle internal server errors."""
        logging.exception("Internal server error")
        return jsonify({'error': 'An internal server error occurred.', 'details': str(e)}), 500

    @app.errorhandler(404)
    def not_found(e):
        """Handle resource not found errors."""
        return jsonify({'error': 'Resource not found.', 'details': str(e)}), 404

    return app
