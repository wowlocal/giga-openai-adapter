import os
import functools
from flask import request, jsonify
from app.config import logger

# Get API keys from environment variables or use a default for development
API_KEYS = os.getenv('API_KEYS', '').split(',')
if not API_KEYS or (len(API_KEYS) == 1 and not API_KEYS[0]):
    # If no API keys are set, use a default key for development
    default_key = "dev-api-key-change-me-in-production"
    API_KEYS = [default_key]
    logger.warning(f"No API keys configured. Using default development key: {default_key}")
else:
    logger.info(f"Loaded {len(API_KEYS)} API keys")

def require_api_key(f):
    """
    Decorator to require a valid API key for access to API endpoints.
    The API key should be provided in the 'Authorization' header as 'Bearer YOUR_API_KEY'.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Get the API key from the Authorization header
        auth_header = request.headers.get('Authorization')

        # Check if Authorization header exists
        if not auth_header:
            logger.warning("API request missing Authorization header")
            return jsonify({
                "error": {
                    "message": "API key is required. Provide it in the Authorization header as 'Bearer YOUR_API_KEY'",
                    "type": "authentication_error",
                    "param": None,
                    "code": "api_key_required"
                }
            }), 401

        # Check if the Authorization header has the correct format
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            logger.warning("Invalid Authorization header format")
            return jsonify({
                "error": {
                    "message": "Invalid Authorization header format. Use 'Bearer YOUR_API_KEY'",
                    "type": "authentication_error",
                    "param": None,
                    "code": "invalid_auth_format"
                }
            }), 401

        # Extract the API key
        api_key = parts[1]

        # Check if the API key is valid
        if api_key not in API_KEYS:
            logger.warning(f"Invalid API key attempted: {api_key[:5]}...")
            return jsonify({
                "error": {
                    "message": "Invalid API key",
                    "type": "authentication_error",
                    "param": None,
                    "code": "invalid_api_key"
                }
            }), 401

        # If the API key is valid, proceed with the request
        return f(*args, **kwargs)

    return decorated_function