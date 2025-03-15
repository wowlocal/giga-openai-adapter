from flask import request, jsonify
from functools import wraps
import os
from app.config import logger

# Get allowed origins from environment variables
ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', '*').split(',')
logger.info(f"CORS allowed origins: {ALLOWED_ORIGINS}")

def cors_headers(response):
    """
    Add CORS headers to a response.

    Args:
        response: Flask response object

    Returns:
        response: Flask response object with CORS headers
    """
    origin = request.headers.get('Origin')

    # Check if the origin is allowed
    if origin and (origin in ALLOWED_ORIGINS or '*' in ALLOWED_ORIGINS):
        response.headers['Access-Control-Allow-Origin'] = origin
    elif '*' in ALLOWED_ORIGINS:
        response.headers['Access-Control-Allow-Origin'] = '*'

    # Allow credentials
    response.headers['Access-Control-Allow-Credentials'] = 'true'

    # Allow specific headers
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'

    # Allow specific methods
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'

    return response

def handle_options_request(f):
    """
    Decorator to handle OPTIONS requests for CORS preflight.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            return cors_headers(response)

        return f(*args, **kwargs)

    return decorated_function

def apply_cors(app):
    """
    Apply CORS protection to a Flask application.

    Args:
        app: Flask application
    """
    # Add CORS headers to all responses
    @app.after_request
    def after_request(response):
        return cors_headers(response)

    # Handle OPTIONS requests
    @app.before_request
    def before_request():
        if request.method == 'OPTIONS':
            response = jsonify({'status': 'ok'})
            return cors_headers(response)

        return None