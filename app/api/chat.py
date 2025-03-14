from flask import Blueprint, request, jsonify, Response, stream_with_context
import json
import traceback
import requests
import asyncio
from app.config import logger
from app.utils.openai_client import get_client
from app.utils.helpers import extract_parameters, generate_completion_id, get_current_timestamp
from gigachat.models import Chat, Messages, MessagesRole, Function, FunctionParameters

# Create a blueprint for the chat API
chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """Handle chat completions requests"""
    try:
        # Log the raw request for debugging
        raw_request = request.get_data(as_text=True)
        try:
            # Try to parse and pretty print the JSON
            parsed_request = json.loads(raw_request)
            pretty_request = json.dumps(parsed_request, indent=2)
            logger.debug(f"Raw request:\n{pretty_request}")

            # Log if request contains tools
            if "tools" in parsed_request:
                logger.warning(f"\033[33m[PROXY] Received request with 'tools' parameter\033[0m")
            if "tool_choice" in parsed_request:
                logger.warning(f"\033[33m[PROXY] Received request with 'tool_choice' parameter\033[0m")

        except json.JSONDecodeError:
            # If not valid JSON, log as is
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

            # Convert OpenAI format to GigaChat format
            gigachat_messages = convert_to_gigachat_messages(request_data['messages'])

            # Prepare tools if present
            functions = None
            if "tools" in request_data:
                functions = convert_to_gigachat_functions(request_data['tools'])

            # Create Chat object for GigaChat
            chat_params = {
                "messages": gigachat_messages,
                "update_interval": 0.1  # For streaming
            }

            # Add optional parameters
            if "temperature" in request_data:
                chat_params["temperature"] = float(request_data["temperature"])
            if "max_tokens" in request_data:
                chat_params["max_tokens"] = int(request_data["max_tokens"])
            if "top_p" in request_data:
                chat_params["top_p"] = float(request_data["top_p"])

            # Add functions if present
            if functions:
                chat_params["functions"] = functions

            chat = Chat(**chat_params)

            # Get a fresh client
            client = get_client()

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

            # Create an event loop for async operations
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Process the stream in an async context and collect results
            async def process_stream():
                result = []
                try:
                    async for chunk in client.astream(chat):
                        # Extract content from the chunk
                        content = ""
                        finish_reason = None
                        tool_calls = None

                        if hasattr(chunk, 'choices') and chunk.choices:
                            for choice in chunk.choices:
                                if hasattr(choice, 'delta') and choice.delta:
                                    if hasattr(choice.delta, 'content') and choice.delta.content:
                                        content = choice.delta.content

                                    # Handle tool calls
                                    if hasattr(choice.delta, 'function_call'):
                                        tool_calls = convert_function_call_to_tool_calls(choice.delta.function_call)
                                        logger.warning(f"\033[33m[PROXY] Received function call in streaming chunk: {json.dumps(tool_calls)}\033[0m")

                                if hasattr(choice, 'finish_reason'):
                                    finish_reason = choice.finish_reason

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

                        # Add tool calls to the chunk if present
                        if tool_calls:
                            formatted_chunk["choices"][0]["delta"]["tool_calls"] = tool_calls

                        result.append(f"data: {json.dumps(formatted_chunk)}\n\n")
                finally:
                    # Ensure we close the client
                    await client.aclose()
                return result

            # Run the async function and get all chunks
            chunks = loop.run_until_complete(process_stream())
            loop.close()

            # Yield all collected chunks
            for chunk in chunks:
                yield chunk

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
        # Convert OpenAI format to GigaChat format
        gigachat_messages = convert_to_gigachat_messages(request_data['messages'])

        # Prepare tools if present
        functions = None
        if "tools" in request_data:
            functions = convert_to_gigachat_functions(request_data['tools'])

        # Create Chat object for GigaChat
        chat_params = {
            "messages": gigachat_messages
        }

        # Add optional parameters
        if "temperature" in request_data:
            chat_params["temperature"] = float(request_data["temperature"])
        if "max_tokens" in request_data:
            chat_params["max_tokens"] = int(request_data["max_tokens"])
        if "top_p" in request_data:
            chat_params["top_p"] = float(request_data["top_p"])

        # Add functions if present
        if functions:
            chat_params["functions"] = functions

        chat = Chat(**chat_params)

        # Get a fresh client
        client = get_client()

        # Create an event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Define an async function to get the response and close the client
        async def get_response():
            try:
                response = await client.achat(chat)
                return response
            finally:
                await client.aclose()

        # Run the async function and get the response
        response = loop.run_until_complete(get_response())
        loop.close()

        # Extract content from the response
        assistant_content = ""
        finish_reason = "stop"
        tool_calls = None

        if hasattr(response, 'choices') and response.choices:
            choice = response.choices[0]
            if hasattr(choice, 'message'):
                message = choice.message
                if hasattr(message, 'content'):
                    assistant_content = message.content

                # Handle function calls if present
                if hasattr(message, 'function_call'):
                    tool_calls = convert_function_call_to_tool_calls(message.function_call)
                    logger.warning(f"\033[33m[PROXY] Received function call in response: {json.dumps(tool_calls)}\033[0m")

            if hasattr(choice, 'finish_reason'):
                finish_reason = choice.finish_reason

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
                "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0) if hasattr(response, 'usage') else 0,
                "completion_tokens": getattr(response.usage, 'completion_tokens', 0) if hasattr(response, 'usage') else 0,
                "total_tokens": getattr(response.usage, 'total_tokens', 0) if hasattr(response, 'usage') else 0
            }
        }

        # Add tool calls to the response if present
        if tool_calls:
            formatted_response["choices"][0]["message"]["tool_calls"] = tool_calls

        logger.debug(f"Formatted response: {json.dumps(formatted_response)}")
        return jsonify(formatted_response)
    except Exception as e:
        logger.error(f"Error in non-stream response: {str(e)}", exc_info=True)
        logger.error(traceback.format_exc())
        raise

def convert_to_gigachat_messages(openai_messages):
    """Convert OpenAI message format to GigaChat message format"""
    gigachat_messages = []

    for msg in openai_messages:
        role = msg.get('role', '').upper()
        if role == 'USER':
            role = MessagesRole.USER
        elif role == 'ASSISTANT':
            role = MessagesRole.ASSISTANT
        elif role == 'SYSTEM':
            role = MessagesRole.SYSTEM
        else:
            # Default to USER for unknown roles
            role = MessagesRole.USER

        gigachat_message = Messages(
            role=role,
            content=msg.get('content', '')
        )
        gigachat_messages.append(gigachat_message)

    return gigachat_messages

def convert_to_gigachat_functions(openai_tools):
    """Convert OpenAI tools format to GigaChat functions format"""
    gigachat_functions = []

    for tool in openai_tools:
        if tool.get('type') == 'function':
            function_data = tool.get('function', {})

            # Convert parameters
            parameters = function_data.get('parameters', {})
            gigachat_parameters = FunctionParameters(
                type=parameters.get('type', 'object'),
                properties=parameters.get('properties', {}),
                required=parameters.get('required', [])
            )

            # Create GigaChat function
            gigachat_function = Function(
                name=function_data.get('name', ''),
                description=function_data.get('description', ''),
                parameters=gigachat_parameters
            )

            gigachat_functions.append(gigachat_function)

    return gigachat_functions

def convert_function_call_to_tool_calls(function_call):
    """Convert GigaChat function call to OpenAI tool calls format"""
    if not function_call:
        return None

    tool_call = {
        "id": generate_completion_id(),
        "type": "function",
        "function": {
            "name": function_call.name if hasattr(function_call, 'name') else "",
            "arguments": function_call.arguments if hasattr(function_call, 'arguments') else "{}"
        }
    }

    return [tool_call]