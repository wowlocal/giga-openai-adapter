from flask import Blueprint, request, jsonify
import json
import traceback
from app.config import logger
from app.utils.openai_client import get_client

# Create a blueprint for the embeddings API
embeddings_bp = Blueprint('embeddings', __name__)

@embeddings_bp.route('/v1/embeddings', methods=['POST'])
def embeddings():
    """Handle embeddings request"""
    try:
        # Log the raw request for debugging
        raw_request = request.get_data(as_text=True)
        logger.debug(f"Raw embeddings request: {raw_request}")

        request_data = request.json
        if not request_data:
            return jsonify({
                "error": {
                    "message": "Invalid JSON in request body",
                    "type": "invalid_request_error",
                    "param": None,
                    "code": "invalid_request_error"
                }
            }), 400

        logger.info(f"Received embeddings request")

        # Check if input is present
        if 'input' not in request_data or not request_data['input']:
            return jsonify({
                "error": {
                    "message": "Input is required",
                    "type": "invalid_request_error",
                    "param": "input",
                    "code": "invalid_request_error"
                }
            }), 400

        # Extract input text(s)
        input_texts = request_data['input']
        if isinstance(input_texts, str):
            input_texts = [input_texts]  # Convert single string to list

        # Extract model name (default to GigaChat-Embeddings)
        model = request_data.get('model', 'GigaChat-Embeddings')

        # Prepare parameters for GigaChat API
        params = {
            "model": model,
            "input": input_texts
        }

        try:
            # Get a fresh client
            client = get_client()

            # Call GigaChat API for embeddings
            response = client.embeddings.create(**params)

            # Get the raw response data
            response_data = response.model_dump()
            logger.debug(f"Raw GigaChat embeddings response: {json.dumps(response_data)}")

            # Format the response to match OpenAI API format
            formatted_response = {
                "object": "list",
                "data": [],
                "model": model,
                "usage": {
                    "prompt_tokens": response_data.get("usage", {}).get("prompt_tokens", 0),
                    "total_tokens": response_data.get("usage", {}).get("total_tokens", 0)
                }
            }

            # Extract embeddings from the response
            if "data" in response_data:
                formatted_response["data"] = response_data["data"]
            else:
                # Fallback if the response structure is different
                for i, embedding in enumerate(response_data.get("embeddings", [])):
                    formatted_response["data"].append({
                        "object": "embedding",
                        "embedding": embedding,
                        "index": i
                    })

            logger.debug(f"Formatted embeddings response: {json.dumps(formatted_response)}")
            return jsonify(formatted_response)

        except Exception as e:
            logger.error(f"Error calling GigaChat embeddings API: {str(e)}", exc_info=True)
            return jsonify({
                "error": {
                    "message": f"Error calling GigaChat embeddings API: {str(e)}",
                    "type": "api_error",
                    "param": None,
                    "code": "api_error"
                }
            }), 502

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in embeddings: {str(e)}", exc_info=True)
        return jsonify({
            "error": {
                "message": f"Invalid JSON: {str(e)}",
                "type": "invalid_request_error",
                "param": None,
                "code": "invalid_request_error"
            }
        }), 400
    except Exception as e:
        logger.error(f"Unexpected error in embeddings: {str(e)}", exc_info=True)
        logger.error(traceback.format_exc())
        return jsonify({
            "error": {
                "message": f"Internal server error: {str(e)}",
                "type": "server_error",
                "param": None,
                "code": "server_error"
            }
        }), 500