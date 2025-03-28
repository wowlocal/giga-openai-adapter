import json
from flask import jsonify
from app.config import logger
from app.utils.helpers import generate_completion_id, get_current_timestamp
from gigachat.models import Messages, MessagesRole, Function, FunctionParameters


def validate_finish_reason(finish_reason):
    """
    Validate that finish_reason is one of the expected values.
    Expected values are: "stop", "length", "tool_calls", "content_filter", or None.
    Logs a warning if the finish_reason is unexpected.

    Note: Warnings are displayed in yellow in the console due to the colored logging
    configuration in app/config/__init__.py.
    """
    expected_values = ["stop", "length", "tool_calls", "content_filter", None]
    if finish_reason not in expected_values:
        logger.warning(f"[PROXY] Unexpected finish_reason value: '{finish_reason}'. Expected one of: {expected_values}")
        # Special case for blacklist finish reason
        if finish_reason == "blacklist":
            logger.info("[PROXY] Converting 'blacklist' finish_reason to 'content_filter'")
            return "content_filter"
        return "stop"
    return finish_reason


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
        elif role == 'TOOL':
            role = MessagesRole.FUNCTION
        else:
            role = MessagesRole.USER  # Default to user for unknown roles

        # Create the base message with content
        gigachat_message = Messages(
            role=role,
            content=msg.get('content', '')
        )

        # Handle tool_calls for assistant messages
        if role == MessagesRole.ASSISTANT and 'tool_calls' in msg and msg['tool_calls']:
            # GigaChat only supports one function call at a time, so we use the first one
            # even if OpenAI format allows multiple tool calls
            tool_call = msg['tool_calls'][0]
            if tool_call.get('type') == 'function':
                function_data = tool_call.get('function', {})

                # Set content to empty string when there's a function call
                gigachat_message.content = ""

                logger.debug(f"Converting tool_call to function_call: {function_data}")
                logger.warning(f"Note: Multiple tool calls were present but only using the first one as GigaChat only supports one function call at a time")

                # Get arguments and parse them if they're a JSON string
                arguments = function_data.get('arguments', '{}')
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                        logger.debug(f"Parsed arguments from JSON string: {arguments}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse arguments as JSON: {e}. Using empty dict.")
                        arguments = {}

                # Create a FunctionCall object
                from gigachat.models import FunctionCall
                gigachat_message.function_call = FunctionCall(
                    name=function_data.get('name', ''),
                    arguments=arguments
                )

                logger.debug(f"Converted tool_call to function_call: {gigachat_message.function_call}")
                if len(msg['tool_calls']) > 1:
                    logger.warning(f"Ignored {len(msg['tool_calls']) - 1} additional tool calls as GigaChat only supports one function call")

        if role == MessagesRole.FUNCTION:
            gigachat_message.content = json.dumps({"result": msg.get('content')}, ensure_ascii=False)
        # For function/tool messages, add the name if present
        if role == MessagesRole.FUNCTION and 'name' in msg:
            gigachat_message.name = msg.get('name')

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

    # Generate an ID with "call_" prefix to match OpenAI format
    call_id = f"call_{generate_completion_id()}"

    # Get the arguments and ensure they're properly formatted as a JSON string
    arguments = getattr(function_call, 'arguments', "{}")

    # Log the original arguments for debugging
    logger.debug(f"Original function call arguments: {arguments} (type: {type(arguments)})")

    # If arguments is already a string, use it directly
    # If it's a dict or other object, convert it to a JSON string
    if not isinstance(arguments, str):
        try:
            arguments = json.dumps(arguments)
            logger.debug(f"Converted arguments to JSON string: {arguments}")
        except Exception as e:
            logger.error(f"Error converting function call arguments to JSON: {str(e)}")
            arguments = "{}"

    # Ensure the arguments are properly escaped if they're not already
    if isinstance(arguments, str) and not arguments.startswith('"'):
        # This means it's not a JSON string yet (it's a raw string)
        try:
            # Parse it first to ensure it's valid JSON
            parsed = json.loads(arguments)
            # Then re-encode it to ensure proper escaping
            arguments = json.dumps(parsed)
            logger.debug(f"Re-encoded arguments for proper escaping: {arguments}")
        except json.JSONDecodeError as e:
            logger.warning(f"Arguments string is not valid JSON, using as is: {str(e)}")

    tool_call = {
        "id": call_id,
        "type": "function",
        "function": {
            "name": getattr(function_call, 'name', ""),
            "arguments": arguments
        }
    }

    logger.debug(f"Final tool call: {json.dumps(tool_call)}")
    return [tool_call]


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
    # Validate finish_reason
    finish_reason = validate_finish_reason(finish_reason)

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

    # Attach content if present (can be empty string)
    # Note: content could be an empty string, which is different from None
    # We should include empty strings in the response
    if content is not None:
        chunk["choices"][0]["delta"]["content"] = content
        logger.debug(f"[PROXY] Adding content to chunk: '{content}'")
    else:
        logger.debug("[PROXY] Content is None, not adding to chunk")

    # Attach tool calls if present
    if tool_calls:
        chunk["choices"][0]["delta"]["tool_calls"] = tool_calls
        # Explicitly set content to null in the delta when tool_calls are present
        chunk["choices"][0]["delta"]["content"] = None
        logger.debug("[PROXY] Adding tool_calls to chunk and setting content to null")

    logger.debug(f"[PROXY] Final chunk structure: {json.dumps(chunk)}")
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
                    finish_reason = "tool_calls"  # Set finish_reason to tool_calls when tool_calls are present
                    assistant_content = None  # Set content to null when tool_calls are present

        finish_reason = getattr(choice, 'finish_reason', "stop") if not tool_calls else "tool_calls"

    # Validate finish_reason
    finish_reason = validate_finish_reason(finish_reason)

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
    content = None  # Initialize as None instead of empty string
    finish_reason = None
    tool_calls = None

    if hasattr(chunk, 'choices') and chunk.choices:
        for choice in chunk.choices:
            if hasattr(choice, 'delta') and choice.delta:
                if hasattr(choice.delta, 'content'):
                    # Even if content is empty string, we should capture it
                    content = choice.delta.content
                    logger.warning(f"[PROXY] Received content in streaming chunk: {content}")

                # Handle function calls separately - don't overwrite content unless necessary
                if hasattr(choice.delta, 'function_call'):
                    tool_calls = convert_function_call_to_tool_calls(choice.delta.function_call)
                    logger.warning(f"[PROXY] Received function call in streaming chunk: {json.dumps(tool_calls)}")
                    # Only set finish_reason for tool_calls, but don't reset content to None
                    # unless there's actually a tool call
                    if tool_calls:
                        finish_reason = "tool_calls"
                        content = None  # Only set content to null if we have actual tool calls

            if hasattr(choice, 'finish_reason'):
                logger.warning(f"[PROXY] Received finish_reason in streaming chunk: {choice.finish_reason}")
                # Only use the choice's finish_reason if we don't have tool_calls
                if not tool_calls:
                    finish_reason = choice.finish_reason

    # Validate finish_reason
    finish_reason = validate_finish_reason(finish_reason)

    logger.debug(f"[PROXY] Extracted from chunk - content: {content}, finish_reason: {finish_reason}, tool_calls: {tool_calls}")
    return content, finish_reason, tool_calls


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