from flask import Blueprint, jsonify
import platform
import datetime
from app.config import logger

# Create a blueprint for the health API
health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify the service is running"""
    try:
        logger.info("Received health check request")

        # Get basic system information
        health_data = {
            "status": "ok",
            "timestamp": datetime.datetime.now().isoformat(),
            "service": "GigaChat API Proxy",
            "python_version": platform.python_version(),
            "system": platform.system(),
            "version": "1.0.0"  # You may want to store this in a config file
        }

        return jsonify(health_data)

    except Exception as e:
        logger.error(f"Error during health check: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": {
                "message": "Health check failed",
                "type": "server_error",
                "code": "server_error"
            }
        }), 500