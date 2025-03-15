from flask import Blueprint, request, jsonify, Response, stream_with_context
import json
import traceback
import requests
import asyncio

from app.config import logger
from app.utils.openai_client import get_client
from app.utils.helpers import generate_completion_id, get_current_timestamp
from gigachat.models import Chat, Messages, MessagesRole, Function, FunctionParameters

# Create a blueprint for the chat API
chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """
    Handle chat completions requests.
    This route supports both streaming and non-streaming responses.
    """
    try:
        log_request_data()
        request_data = request.json

        # Validate request data
        if not request_data:
            return error_response(
                message="Invalid JSON in request body",
                error_type="invalid_request_error",
                code="invalid_request_error",
                status=400
            )

        logger.info("Received chat completion request")

        # Check for required messages
        if 'messages' not in request_data or not request_data['messages']:
            return error_response(
                message="Messages are required",
                error_type="invalid_request_error",
                code="invalid_request_error",
                param="messages",
                status=400
            )

        # Check streaming preference
        stream = request_data.get('stream', False)
        return stream_response(request_data) if stream else non_stream_response(request_data)

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}", exc_info=True)
        return error_response(
            message=f"Invalid JSON: {str(e)}",
            error_type="invalid_request_error",
            code="invalid_request_error",
            status=400
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Error communicating with GigaChat API: {str(e)}", exc_info=True)
        return error_response(
            message=f"Error communicating with GigaChat API: {str(e)}",
            error_type="server_error",
            code="server_error",
            status=500
        )
    except Exception as e:
        logger.error(f"Unexpected error in chat completion: {str(e)}", exc_info=True)
        logger.error(traceback.format_exc())
        return error_response(
            message=f"Internal server error: {str(e)}",
            error_type="server_error",
            code="server_error",
            status=500
        )


def stream_response(request_data):
    """
    Handle streaming response.
    Returns a Response object that streams data (text/event-stream).
    """

    def generate():
        try:
            completion_id = generate_completion_id()
            created_time = get_current_timestamp()

            chat_params = build_chat_params(request_data, streaming=True)
            chat = Chat(**chat_params)

            # Send the first chunk with the 'assistant' role
            first_chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created_time,
                "model": "GigaChat",
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant"},
                        "finish_reason": None
                    }
                ]
            }
            yield f"data: {json.dumps(first_chunk)}\n\n"

            # Create an event loop and process streaming
            client = get_client()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def process_stream():
                chunks_collected = []
                try:
                    async for chunk in client.astream(chat):
                        content, finish_reason, tool_calls = parse_chunk_fields(chunk)
                        formatted_chunk = build_stream_chunk(
                            completion_id,
                            created_time,
                            content,
                            finish_reason,
                            tool_calls
                        )
                        chunks_collected.append(f"data: {json.dumps(formatted_chunk)}\n\n")
                finally:
                    await client.aclose()
                return chunks_collected

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
            yield error_stream_chunk(str(e))

    return Response(stream_with_context(generate()), mimetype='text/event-stream')


def non_stream_response(request_data):
    """
    Handle non-streaming response.
    Returns a standard JSON response.
    """
    try:
        chat_params = build_chat_params(request_data, streaming=False)
        chat = Chat(**chat_params)

        client = get_client()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def get_response():
            try:
                return await client.achat(chat)
            finally:
                await client.aclose()

        response = loop.run_until_complete(get_response())
        loop.close()

        return jsonify(build_non_stream_json(response))

    except Exception as e:
        logger.error(f"Error in non-stream response: {str(e)}", exc_info=True)
        logger.error(traceback.format_exc())
        raise


def build_chat_params(request_data, streaming=False):
    """
    Build and return a dict of parameters suitable for instantiating a Chat object.
    """
    gigachat_messages = convert_to_gigachat_messages(request_data['messages'])
    functions = None

    if "tools" in request_data:
        functions = convert_to_gigachat_functions(request_data['tools'])

    chat_params = {
        "messages": gigachat_messages
    }

    # If streaming, set update_interval
    if streaming:
        chat_params["update_interval"] = 0.1

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

    return chat_params


def build_stream_chunk(completion_id, created_time, content, finish_reason, tool_calls):
    """
    Format a single chunk for streaming in the OpenAI-compatible format.
    """
    chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created_time,
        "model": "GigaChat",
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": finish_reason
            }
        ]
    }

    # Attach content if present
    if content:
        chunk["choices"][0]["delta"]["content"] = content

    # Attach tool calls if present
    if tool_calls:
        chunk["choices"][0]["delta"]["tool_calls"] = tool_calls

    return chunk


def build_non_stream_json(response):
    """
    Build and return the JSON for non-streaming responses in OpenAI-compatible format.
    """
    completion_id = generate_completion_id()
    created_time = get_current_timestamp()

    assistant_content = ""
    finish_reason = "stop"
    tool_calls = None

    # Extract details from the response
    if hasattr(response, 'choices') and response.choices:
        choice = response.choices[0]
        if hasattr(choice, 'message'):
            message = choice.message
            assistant_content = getattr(message, 'content', "")

            # Handle function calls
            if hasattr(message, 'function_call'):
                tool_calls = convert_function_call_to_tool_calls(message.function_call)
                if tool_calls:
                    logger.warning(f"[PROXY] Received function call in response: {json.dumps(tool_calls)}")

        finish_reason = getattr(choice, 'finish_reason', "stop")

    usage_data = {
        "prompt_tokens": getattr(response.usage, 'prompt_tokens', 0) if hasattr(response, 'usage') else 0,
        "completion_tokens": getattr(response.usage, 'completion_tokens', 0) if hasattr(response, 'usage') else 0,
        "total_tokens": getattr(response.usage, 'total_tokens', 0) if hasattr(response, 'usage') else 0,
    }

    result = {
        "id": completion_id,
        "object": "chat.completion",
        "created": created_time,
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
        "usage": usage_data
    }

    # Add tool calls if present
    if tool_calls:
        result["choices"][0]["message"]["tool_calls"] = tool_calls

    logger.debug(f"Formatted response: {json.dumps(result)}")
    return result


def parse_chunk_fields(chunk):
    """
    Extract content, finish_reason, and tool_calls from an async chunk in the streaming response.
    """
    content = ""
    finish_reason = None
    tool_calls = None

    if hasattr(chunk, 'choices') and chunk.choices:
        for choice in chunk.choices:
            if hasattr(choice, 'delta') and choice.delta:
                if hasattr(choice.delta, 'content') and choice.delta.content:
                    content = choice.delta.content
                if hasattr(choice.delta, 'function_call'):
                    tool_calls = convert_function_call_to_tool_calls(choice.delta.function_call)
                    logger.warning(f"[PROXY] Received function call in streaming chunk: {json.dumps(tool_calls)}")
            if hasattr(choice, 'finish_reason'):
                finish_reason = choice.finish_reason
    return content, finish_reason, tool_calls


def convert_to_gigachat_messages(openai_messages):
    """
    Convert OpenAI message format to GigaChat message format.
    """
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
            role = MessagesRole.USER  # Default to user for unknown roles

        gigachat_message = Messages(
            role=role,
            content=msg.get('content', '')
        )
        gigachat_messages.append(gigachat_message)

    return gigachat_messages


def convert_to_gigachat_functions(openai_tools):
    """
    Convert OpenAI 'tools' format to GigaChat 'functions' format.
    """
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

            gigachat_function = Function(
                name=function_data.get('name', ''),
                description=function_data.get('description', ''),
                parameters=gigachat_parameters
            )

            gigachat_functions.append(gigachat_function)

    return gigachat_functions


def convert_function_call_to_tool_calls(function_call):
    """
    Convert GigaChat function call to OpenAI tool calls format.
    """
    if not function_call:
        return None

    tool_call = {
        "id": generate_completion_id(),
        "type": "function",
        "function": {
            "name": getattr(function_call, 'name', ""),
            "arguments": getattr(function_call, 'arguments', "{}")
        }
    }
    return [tool_call]


def log_request_data():
    """
    Log the raw request data for debugging.
    """
    raw_request = request.get_data(as_text=True)
    try:
        parsed_request = json.loads(raw_request)
        pretty_request = json.dumps(parsed_request, indent=2)
        logger.debug(f"Raw request:\n{pretty_request}")

        if "tools" in parsed_request:
            logger.warning("[PROXY] Received request with 'tools' parameter")
        if "tool_choice" in parsed_request:
            logger.warning("[PROXY] Received request with 'tool_choice' parameter")

    except json.JSONDecodeError:
        logger.debug(f"Raw request: {raw_request}")


def error_stream_chunk(message):
    """
    Build a streaming-compatible error chunk and return it,
    followed by the '[DONE]' sentinel.
    """
    error_chunk = {
        "error": {
            "message": f"Error: {message}",
            "type": "server_error",
            "param": None,
            "code": "server_error"
        }
    }
    return f"data: {json.dumps(error_chunk)}\n\ndata: [DONE]\n\n"


def error_response(
    message,
    error_type,
    code,
    status=500,
    param=None
):
    """
    Return a standardized error response in OpenAI-compatible format.
    """
    error_body = {
        "error": {
            "message": message,
            "type": error_type,
            "param": param,
            "code": code
        }
    }
    return jsonify(error_body), status
