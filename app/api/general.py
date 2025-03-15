from flask import Blueprint, request, jsonify, Response
import traceback
from app.config import GIGACHAT_BASE_URL, logger
from app.auth.token_manager import token_manager
from app.utils.ssl import create_http_client

# Create a blueprint for the general API
general_bp = Blueprint('general', __name__)

@general_bp.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'])
def general_proxy(path):
    """General proxy endpoint that forwards any request to the GigaChat API"""
    # Log the path and return 404
    logger.info(f"Received request for unsupported path: {path}, method: {request.method}")
    return jsonify({
        "error": {
            "message": f"Path not found: {path}",
            "type": "not_found_error",
            "code": "not_found_error"
        }
    }), 404
def ____general_proxy(path):
    logger.info(f"Received request for path: {path}, method: {request.method}")
    """General proxy endpoint that forwards any request to the GigaChat API"""
    try:
        # Log the incoming request
        logger.info(f"Received request for path: {path}, method: {request.method}")
        raw_request = request.get_data(as_text=True)
        if raw_request:
            logger.debug(f"Raw request data: {raw_request}")

        # Construct the target URL
        target_url = f"{GIGACHAT_BASE_URL}/api/{path}"
        logger.info(f"Forwarding to: {target_url}")

        # Create HTTP client with proper SSL verification
        http_client = create_http_client()

        # Get the headers from the original request
        headers = {key: value for key, value in request.headers.items()
                  if key.lower() not in ['host', 'content-length']}

        # Add authorization header with the token
        headers['Authorization'] = f"Bearer {token_manager.get_valid_token()}"

        # Get the request data
        data = request.get_data()

        # Forward the request to the GigaChat API using our http_client with proper SSL verification
        response = http_client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=data,
            params=request.args
        )

        # Log the response status
        logger.info(f"GigaChat API responded with status: {response.status_code}")

        # Create a Flask response with the same content and status code
        flask_response = Response(
            response=response.content,
            status=response.status_code,
            headers=dict(response.headers)
        )

        return flask_response

    except Exception as e:
        logger.error(f"Error in general proxy: {str(e)}", exc_info=True)
        logger.error(traceback.format_exc())
        return jsonify({
            "error": {
                "message": f"Error proxying request: {str(e)}",
                "type": "server_error",
                "code": "server_error"
            }
        }), 500

# Special case for /api/version endpoint
@general_bp.route('/api/version', methods=['GET'])
def api_version():
    """Return API version information"""
    return jsonify({
        "version": "1.0.0",
        "name": "GigaChat API Proxy",
        "description": "Proxy server for GigaChat API"
    })