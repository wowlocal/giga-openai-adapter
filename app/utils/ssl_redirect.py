from flask import request, redirect, current_app
import os
from app.config import logger

# Get SSL configuration from environment variables
FORCE_SSL = os.getenv('FORCE_SSL', 'false').lower() == 'true'
logger.info(f"Force SSL: {FORCE_SSL}")

class SSLRedirect:
    """
    Middleware to redirect HTTP requests to HTTPS.
    """
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """
        Initialize the middleware with a Flask application.

        Args:
            app: Flask application
        """
        app.before_request(self.redirect_to_https)

    def redirect_to_https(self):
        """
        Redirect HTTP requests to HTTPS.
        """
        # Only redirect if FORCE_SSL is enabled
        if not FORCE_SSL:
            return None

        # Check if the request is secure
        if request.is_secure:
            return None

        # Check if the request is from a proxy
        if request.headers.get('X-Forwarded-Proto') == 'https':
            return None

        # Redirect to HTTPS
        url = request.url.replace('http://', 'https://', 1)
        logger.info(f"Redirecting HTTP request to HTTPS: {url}")
        return redirect(url, code=301)

def init_ssl_redirect(app):
    """
    Initialize SSL redirection for a Flask application.

    Args:
        app: Flask application
    """
    ssl_redirect = SSLRedirect()
    ssl_redirect.init_app(app)