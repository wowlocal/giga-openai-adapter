import uuid
import time
import json
from app.config import logger

def extract_parameters(request_data, default_model="GigaChat"):
    """Extract parameters from the request data"""
    params = {
        "model": request_data.get("model", default_model),
        "messages": request_data['messages'],
    }

    # Add optional parameters if they exist in the request
    optional_params = [
        "temperature", "max_tokens", "top_p",
        "frequency_penalty", "presence_penalty", "stop"
    ]

    for param in optional_params:
        if param in request_data:
            # Convert to appropriate type
            if param in ["temperature", "top_p", "frequency_penalty", "presence_penalty"]:
                params[param] = float(request_data[param])
            elif param == "max_tokens":
                params[param] = int(request_data[param])
            else:
                params[param] = request_data[param]

    logger.debug(f"Extracted parameters: {json.dumps(params)}")
    return params

def generate_completion_id():
    """Generate a unique ID for a completion"""
    return f"chatcmpl-{str(uuid.uuid4())[:10]}"

def get_current_timestamp():
    """Get the current timestamp in seconds"""
    return int(time.time())