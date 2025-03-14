from flask import jsonify
import json
import traceback
from app.config import logger

def register_error_handlers(app):
    """Register error handlers for the Flask application"""

    @app.errorhandler(400)
    def bad_request(error):
        logger.error(f"Bad request: {str(error)}")
        return jsonify({
            "error": {
                "message": f"Bad request: {str(error)}",
                "type": "invalid_request_error",
                "param": None,
                "code": "invalid_request_error"
            }
        }), 400

    @app.errorhandler(404)
    def not_found(error):
        logger.error(f"Not found: {str(error)}")
        return jsonify({
            "error": {
                "message": f"Not found: {str(error)}",
                "type": "invalid_request_error",
                "param": None,
                "code": "invalid_request_error"
            }
        }), 404

    @app.errorhandler(500)
    def server_error(error):
        logger.error(f"Server error: {str(error)}")
        logger.error(traceback.format_exc())
        return jsonify({
            "error": {
                "message": f"Internal server error: {str(error)}",
                "type": "server_error",
                "param": None,
                "code": "server_error"
            }
        }), 500

    @app.errorhandler(json.JSONDecodeError)
    def json_decode_error(error):
        logger.error(f"JSON decode error: {str(error)}")
        return jsonify({
            "error": {
                "message": f"Invalid JSON: {str(error)}",
                "type": "invalid_request_error",
                "param": None,
                "code": "invalid_request_error"
            }
        }), 400