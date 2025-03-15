import time
import threading
from flask import request, jsonify
import functools
from app.config import logger
import os

# Get rate limit configuration from environment variables
DEFAULT_RATE_LIMIT = int(os.getenv('DEFAULT_RATE_LIMIT', '60'))  # requests per minute
DEFAULT_RATE_WINDOW = int(os.getenv('DEFAULT_RATE_WINDOW', '60'))  # window in seconds

class RateLimiter:
    """
    Simple in-memory rate limiter to protect API endpoints from abuse.
    Uses a sliding window approach to track requests.
    """
    def __init__(self, limit=DEFAULT_RATE_LIMIT, window=DEFAULT_RATE_WINDOW):
        """
        Initialize the rate limiter.

        Args:
            limit (int): Maximum number of requests allowed in the window
            window (int): Time window in seconds
        """
        self.limit = limit
        self.window = window
        self.requests = {}  # {ip: [timestamp1, timestamp2, ...]}
        self.lock = threading.Lock()

    def is_rate_limited(self, key):
        """
        Check if a key (IP address or API key) is rate limited.

        Args:
            key (str): The key to check (usually IP address or API key)

        Returns:
            tuple: (is_limited, remaining, reset_time)
        """
        now = time.time()

        with self.lock:
            # Initialize if this is the first request from this key
            if key not in self.requests:
                self.requests[key] = []

            # Remove timestamps outside the current window
            self.requests[key] = [ts for ts in self.requests[key] if now - ts < self.window]

            # Check if the key has exceeded the rate limit
            if len(self.requests[key]) >= self.limit:
                # Calculate when the rate limit will reset
                oldest_timestamp = min(self.requests[key]) if self.requests[key] else now
                reset_time = oldest_timestamp + self.window
                return True, 0, reset_time

            # Add the current timestamp to the list
            self.requests[key].append(now)

            # Calculate remaining requests
            remaining = self.limit - len(self.requests[key])

            # Calculate when the rate limit will reset
            reset_time = now + self.window

            return False, remaining, reset_time

# Create a global rate limiter instance
rate_limiter = RateLimiter()

def rate_limit(f):
    """
    Decorator to apply rate limiting to API endpoints.
    Rate limits are applied per IP address by default.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Get the client's IP address
        client_ip = request.remote_addr

        # Get API key if available (for per-key rate limiting)
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            # Use API key as the rate limit key if available
            rate_limit_key = auth_header.split(' ')[1]
        else:
            # Fall back to IP address
            rate_limit_key = client_ip

        # Check if the client is rate limited
        is_limited, remaining, reset_time = rate_limiter.is_rate_limited(rate_limit_key)

        # Set rate limit headers
        response = None

        if is_limited:
            logger.warning(f"Rate limit exceeded for {rate_limit_key}")
            response = jsonify({
                "error": {
                    "message": "Rate limit exceeded. Please try again later.",
                    "type": "rate_limit_error",
                    "param": None,
                    "code": "rate_limit_exceeded"
                }
            })
            response.status_code = 429
        else:
            # Proceed with the request
            response = f(*args, **kwargs)

        # Add rate limit headers to the response
        if hasattr(response, 'headers'):
            response.headers['X-RateLimit-Limit'] = str(rate_limiter.limit)
            response.headers['X-RateLimit-Remaining'] = str(remaining)
            response.headers['X-RateLimit-Reset'] = str(int(reset_time))

        return response

    return decorated_function