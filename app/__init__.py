from flask import Flask

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)

    # Import and register blueprints
    from app.api.models import models_bp
    from app.api.chat import chat_bp
    from app.api.embeddings import embeddings_bp
    from app.api.general import general_bp

    app.register_blueprint(models_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(embeddings_bp)
    app.register_blueprint(general_bp)

    # Register error handlers
    from app.utils.error_handlers import register_error_handlers
    register_error_handlers(app)

    return app