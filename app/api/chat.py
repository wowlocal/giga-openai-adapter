from flask import Blueprint, request, jsonify, Response, stream_with_context
import json
import traceback
import requests
import asyncio

from app.config import logger
from app.utils.openai_client import get_client
from app.utils.helpers import generate_completion_id, get_current_timestamp
from app.utils.mapping import (
    build_chat_params,
    build_stream_chunk,
    build_non_stream_json,
    parse_chunk_fields,
    convert_function_call_to_tool_calls,
    error_stream_chunk,
    error_response,
    convert_to_gigachat_messages,
    convert_to_gigachat_functions
)
from gigachat.models import Chat

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

DEBUG_STREAM_DELAY = 0.0

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

            # Create a queue to communicate between async and sync worlds
            queue = asyncio.Queue()

            async def process_stream():
                try:
                    async for chunk in client.astream(chat):
                        logger.debug(f"[PROXY] Raw chunk from GigaChat: {chunk}")
                        content, finish_reason, tool_calls = parse_chunk_fields(chunk)
                        formatted_chunk = build_stream_chunk(
                            completion_id,
                            created_time,
                            content,
                            finish_reason,
                            tool_calls
                        )
                        logger.debug(f"[PROXY] Formatted chunk: {formatted_chunk}")
                        await queue.put(f"data: {json.dumps(formatted_chunk)}\n\n")
                    # Signal that we're done
                    await queue.put(None)
                except Exception as e:
                    logger.error(f"Error in async stream processing: {str(e)}", exc_info=True)
                    await queue.put(error_stream_chunk(str(e)))
                    await queue.put(None)
                finally:
                    await client.aclose()

            # Start the async task
            task = loop.create_task(process_stream())

            # Process chunks as they arrive
            import time
            while True:
                try:
                    # Get the next chunk from the queue with a timeout
                    chunk = loop.run_until_complete(asyncio.wait_for(queue.get(), timeout=30.0))
                    if chunk is None:  # End of stream
                        break
                    yield chunk
                    # Add a small delay between chunks if DEBUG_STREAM_DELAY is enabled
                    if DEBUG_STREAM_DELAY > 0:
                        time.sleep(DEBUG_STREAM_DELAY)
                        logger.debug(f"Sent chunk with delay of {DEBUG_STREAM_DELAY}s")
                except asyncio.TimeoutError:
                    logger.warning("Timeout waiting for next chunk, ending stream")
                    break
                except Exception as e:
                    logger.error(f"Error processing chunk: {str(e)}", exc_info=True)
                    yield error_stream_chunk(str(e))
                    break

            # Clean up
            if not task.done():
                task.cancel()
            loop.close()

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
