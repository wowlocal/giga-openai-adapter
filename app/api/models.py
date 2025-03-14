from flask import Blueprint, jsonify
import httpx
from app.config import GIGACHAT_API_V1_URL, logger
from app.auth.token_manager import token_manager
from app.utils.ssl import create_http_client

# Create a blueprint for the models API
models_bp = Blueprint('models', __name__)

@models_bp.route('/v1/models', methods=['GET'])
def list_models():
    """List available models from GigaChat API"""
    try:
        logger.info("Received request to list models")

        # Create HTTP client with proper SSL verification
        http_client = create_http_client()

        # Make a request to GigaChat API to get available models
        try:
            response = http_client.get(
                f"{GIGACHAT_API_V1_URL}/models",
                headers={"Authorization": f"Bearer {token_manager.get_valid_token()}"}
            )
            response.raise_for_status()
            models_data = response.json()
            logger.info(f"Successfully fetched models from GigaChat API")
            return jsonify(models_data)
        except httpx.HTTPError as e:
            logger.error(f"Error fetching models from GigaChat API: {str(e)}", exc_info=True)
            return jsonify({
                "error": {
                    "message": f"Failed to fetch models from GigaChat API: {str(e)}",
                    "type": "api_error",
                    "param": None,
                    "code": "api_error"
                }
            }), 502

    except Exception as e:
        logger.error(f"Error listing models: {str(e)}", exc_info=True)
        return jsonify({
            "error": {
                "message": "Failed to fetch models",
                "type": "server_error",
                "param": None,
                "code": "server_error"
            }
        }), 500