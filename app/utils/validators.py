import functools
from flask import request, jsonify
from app.config import logger
import json

def validate_json(f):
    """
    Decorator to validate that the request contains valid JSON.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if the request has a JSON body
        if not request.is_json:
            logger.warning("Request does not contain JSON")
            return jsonify({
                "error": {
                    "message": "Request must be JSON",
                    "type": "invalid_request_error",
                    "param": None,
                    "code": "invalid_request_error"
                }
            }), 400

        # Try to parse the JSON
        try:
            _ = request.get_json()
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in request: {str(e)}")
            return jsonify({
                "error": {
                    "message": f"Invalid JSON in request: {str(e)}",
                    "type": "invalid_request_error",
                    "param": None,
                    "code": "invalid_request_error"
                }
            }), 400

        return f(*args, **kwargs)

    return decorated_function

def validate_chat_request(f):
    """
    Decorator to validate that the chat completion request contains required fields.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # First validate that the request contains valid JSON
        if not request.is_json:
            logger.warning("Chat request does not contain JSON")
            return jsonify({
                "error": {
                    "message": "Request must be JSON",
                    "type": "invalid_request_error",
                    "param": None,
                    "code": "invalid_request_error"
                }
            }), 400

        # Get the request data
        request_data = request.get_json()

        # Check for required fields
        if 'messages' not in request_data or not request_data['messages']:
            logger.warning("Chat request missing 'messages' field")
            return jsonify({
                "error": {
                    "message": "Missing required field: messages",
                    "type": "invalid_request_error",
                    "param": "messages",
                    "code": "invalid_request_error"
                }
            }), 400

        # Validate messages format
        messages = request_data['messages']
        if not isinstance(messages, list):
            logger.warning("Chat request 'messages' field is not a list")
            return jsonify({
                "error": {
                    "message": "Field 'messages' must be a list",
                    "type": "invalid_request_error",
                    "param": "messages",
                    "code": "invalid_request_error"
                }
            }), 400

        # Validate each message
        for i, message in enumerate(messages):
            if not isinstance(message, dict):
                logger.warning(f"Chat request message {i} is not an object")
                return jsonify({
                    "error": {
                        "message": f"Message at index {i} must be an object",
                        "type": "invalid_request_error",
                        "param": f"messages[{i}]",
                        "code": "invalid_request_error"
                    }
                }), 400

            # Check for required fields in each message
            if 'role' not in message:
                logger.warning(f"Chat request message {i} missing 'role' field")
                return jsonify({
                    "error": {
                        "message": f"Message at index {i} missing required field: role",
                        "type": "invalid_request_error",
                        "param": f"messages[{i}].role",
                        "code": "invalid_request_error"
                    }
                }), 400

            if 'content' not in message and message['role'] != 'system':
                logger.warning(f"Chat request message {i} missing 'content' field")
                return jsonify({
                    "error": {
                        "message": f"Message at index {i} missing required field: content",
                        "type": "invalid_request_error",
                        "param": f"messages[{i}].content",
                        "code": "invalid_request_error"
                    }
                }), 400

            # Validate role values
            valid_roles = ['system', 'user', 'assistant', 'function', 'tool']
            if message['role'] not in valid_roles:
                logger.warning(f"Chat request message {i} has invalid role: {message['role']}")
                return jsonify({
                    "error": {
                        "message": f"Invalid role in message at index {i}. Must be one of: {', '.join(valid_roles)}",
                        "type": "invalid_request_error",
                        "param": f"messages[{i}].role",
                        "code": "invalid_request_error"
                    }
                }), 400

        # If all validations pass, proceed with the request
        return f(*args, **kwargs)

    return decorated_function