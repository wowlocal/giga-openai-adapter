from app import create_app
from app.utils.ssl import cleanup_cert_bundle
from app.config import logger

# Create the Flask application - this is used by Gunicorn
app = create_app()

if __name__ == '__main__':
    try:
        # When running directly (development only)
        logger.info("Starting proxy server on port 3001 (development mode)")
        app.run(host='0.0.0.0', port=3001, debug=True)
    finally:
        # Clean up resources
        cleanup_cert_bundle()