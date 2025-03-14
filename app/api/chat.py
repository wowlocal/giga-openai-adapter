from flask import Blueprint, request, jsonify, Response, stream_with_context
import json
import traceback
import requests
from app.config import logger
from app.utils.openai_client import get_client
from app.utils.helpers import extract_parameters, generate_completion_id, get_current_timestamp

# Create a blueprint for the chat API
chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """Handle chat completions requests"""
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

        logger.info(f"Received chat completion request")

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

def stream_response(request_data):
    """Handle streaming response"""
    def generate():
        try:
            # Create a unique ID for this completion
            completion_id = generate_completion_id()
            created_time = get_current_timestamp()

            # Extract parameters from request
            params = extract_parameters(request_data)
            params['stream'] = True

            # Get a fresh client
            client = get_client()

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

        # Get a fresh client
        client = get_client()

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
            "id": generate_completion_id(),
            "object": "chat.completion",
            "created": get_current_timestamp(),
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