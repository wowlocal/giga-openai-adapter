from flask import Flask, request, jsonify, Response, stream_with_context
import requests
import os
import logging
from dotenv import load_dotenv
import time
import uuid
import json
import traceback

from openai import OpenAI
import httpx

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

ssl_context = httpx.create_ssl_context(verify=False)
http_client = httpx.Client(verify=False)

class TokenManager:
    def __init__(self, master_token):
        self.master_token = master_token
        self.access_token = None
        self.expires_at = None

    def get_valid_token(self):
        """Get a valid token, refreshing if necessary"""
        if not self.access_token or not self.expires_at or time.time() * 1000 >= self.expires_at:
            logger.info("Token expired or not set, refreshing...")
            self.refresh_token()
        return self.access_token

    def refresh_token(self):
        """Get new access token from Sberbank OAuth endpoint"""
        try:
            # Encode master token in base64 for Basic auth
            auth_string = f"Basic {self.master_token}"

            # Prepare headers
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json',
                'RqUID': str(uuid.uuid4()),
                'Authorization': auth_string
            }

            # Prepare data
            data = {
                'scope': 'GIGACHAT_API_PERS'
            }

            # Make request to OAuth endpoint
            response = http_client.post(
                'https://ngw.devices.sberbank.ru:9443/api/v2/oauth',
                headers=headers,
                data=data
            )
            response.raise_for_status()

            # Parse response
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.expires_at = token_data['expires_at']
            logger.info("Successfully obtained new access token")
            return self.access_token

        except Exception as e:
            logger.error(f"Error getting access token: {str(e)}", exc_info=True)
            raise

# Load environment variables from .env file
load_dotenv()

# Get master token from environment variable
MASTER_TOKEN = os.getenv('MASTER_TOKEN')
if not MASTER_TOKEN:
    raise ValueError("MASTER_TOKEN environment variable is not set")

# Initialize token manager
token_manager = TokenManager(MASTER_TOKEN)

# Initialize OpenAI client with initial token
client = OpenAI(api_key=token_manager.get_valid_token(),
                base_url="https://gigachat.devices.sberbank.ru/api/v1",
                http_client=http_client
                )

app = Flask(__name__)

@app.route('/v1/models', methods=['GET'])
def list_models():
    try:
        logger.info("Received request to list models")

        # Make a request to GigaChat API to get available models
        try:
            response = http_client.get(
                "https://gigachat.devices.sberbank.ru/api/v1/models",
                headers={"Authorization": f"Bearer {token_manager.get_valid_token()}"}
            )
            response.raise_for_status()
            models_data = response.json()
            logger.info(f"Successfully fetched models from GigaChat API: {json.dumps(models_data)}")
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

@app.route('/v1/chat/completions', methods=['POST'])
def proxy():
    try:
        # Log the raw request for debugging
        raw_request = request.get_data(as_text=True)
        logger.debug(f"Raw request: {raw_request}")

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

        logger.info(f"Received chat completion request: {json.dumps(request_data)}")

        # Check if messages are present
        if 'messages' not in request_data or not request_data['messages']:
            return jsonify({
                "error": {
                    "message": "Messages are required",
                    "type": "invalid_request_error",
                    "param": "messages",
                    "code": "invalid_request_error"
                }
            }), 400

        # Check if streaming is requested
        stream = request_data.get('stream', False)

        if stream:
            return stream_response(request_data)
        else:
            return non_stream_response(request_data)

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}", exc_info=True)
        return jsonify({
            "error": {
                "message": f"Invalid JSON: {str(e)}",
                "type": "invalid_request_error",
                "param": None,
                "code": "invalid_request_error"
            }
        }), 400
    except requests.exceptions.RequestException as e:
        logger.error(f"Error communicating with GigaChat API: {str(e)}", exc_info=True)
        return jsonify({
            "error": {
                "message": f"Error communicating with GigaChat API: {str(e)}",
                "type": "server_error",
                "param": None,
                "code": "server_error"
            }
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error in chat completion: {str(e)}", exc_info=True)
        logger.error(traceback.format_exc())
        return jsonify({
            "error": {
                "message": f"Internal server error: {str(e)}",
                "type": "server_error",
                "param": None,
                "code": "server_error"
            }
        }), 500

def extract_parameters(request_data):
    """Extract parameters from the request data"""
    params = {
        "model": "GigaChat",
        "messages": request_data['messages'],
    }

    # Add optional parameters if they exist in the request
    if 'temperature' in request_data:
        params['temperature'] = float(request_data['temperature'])

    if 'max_tokens' in request_data:
        params['max_tokens'] = int(request_data['max_tokens'])

    if 'top_p' in request_data:
        params['top_p'] = float(request_data['top_p'])

    if 'frequency_penalty' in request_data:
        params['frequency_penalty'] = float(request_data['frequency_penalty'])

    if 'presence_penalty' in request_data:
        params['presence_penalty'] = float(request_data['presence_penalty'])

    if 'stop' in request_data:
        params['stop'] = request_data['stop']

    logger.debug(f"Extracted parameters: {json.dumps(params)}")
    return params

def stream_response(request_data):
    """Handle streaming response"""
    def generate():
        try:
            # Create a unique ID for this completion
            completion_id = f"chatcmpl-{str(uuid.uuid4())[:10]}"
            created_time = int(time.time())

            # Extract parameters from request
            params = extract_parameters(request_data)
            params['stream'] = True

            # Call GigaChat API with streaming enabled
            stream_resp = client.chat.completions.create(**params)

            # Send the first chunk with role
            first_chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created_time,
                "model": "GigaChat",
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "role": "assistant"
                        },
                        "finish_reason": None
                    }
                ]
            }
            yield f"data: {json.dumps(first_chunk)}\n\n"

            # Process each chunk from the stream
            for chunk in stream_resp:
                chunk_data = chunk.model_dump()
                # logger.debug(f"Stream chunk: {json.dumps(chunk_data)}")

                # Extract content from the chunk
                content = ""
                finish_reason = None
                if chunk_data.get("choices") and len(chunk_data["choices"]) > 0:
                    choice = chunk_data["choices"][0]
                    delta = choice.get("delta", {})
                    content = delta.get("content", "")
                    finish_reason = choice.get("finish_reason")

                # Format as OpenAI API streaming response
                formatted_chunk = {
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": "GigaChat",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "content": content
                            },
                            "finish_reason": finish_reason
                        }
                    ]
                }

                yield f"data: {json.dumps(formatted_chunk)}\n\n"

            # Send the final [DONE] message
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Error in stream generation: {str(e)}", exc_info=True)
            logger.error(traceback.format_exc())
            error_chunk = {
                "error": {
                    "message": f"Error: {str(e)}",
                    "type": "server_error",
                    "param": None,
                    "code": "server_error"
                }
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
            yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

def non_stream_response(request_data):
    """Handle non-streaming response"""
    try:
        # Extract parameters from request
        params = extract_parameters(request_data)

        # Forward the request to the GigaChat API
        response = client.chat.completions.create(**params)

        # Get the raw response data
        response_data = response.model_dump()
        logger.debug(f"Raw GigaChat response: {json.dumps(response_data)}")

        # Extract content from the response
        assistant_content = ""
        finish_reason = "stop"
        if response_data.get("choices") and len(response_data["choices"]) > 0:
            choice = response_data["choices"][0]
            message = choice.get("message", {})
            assistant_content = message.get("content", "")
            if choice.get("finish_reason"):
                finish_reason = choice.get("finish_reason")

        # Format the response to match OpenAI API format
        formatted_response = {
            "id": f"chatcmpl-{str(uuid.uuid4())[:10]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "GigaChat",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": assistant_content
                    },
                    "finish_reason": finish_reason
                }
            ],
            "usage": {
                "prompt_tokens": response_data.get("usage", {}).get("prompt_tokens", 0),
                "completion_tokens": response_data.get("usage", {}).get("completion_tokens", 0),
                "total_tokens": response_data.get("usage", {}).get("total_tokens", 0)
            }
        }

        logger.debug(f"Formatted response: {json.dumps(formatted_response)}")
        return jsonify(formatted_response)
    except Exception as e:
        logger.error(f"Error in non-stream response: {str(e)}", exc_info=True)
        logger.error(traceback.format_exc())
        raise

if __name__ == '__main__':
    logger.info("Starting proxy server on port 3000")
    app.run(host='0.0.0.0', port=3000, debug=True)
