from app import create_app
from app.utils.ssl import cleanup_cert_bundle
from app.config import logger

if __name__ == '__main__':
    try:
        # Create the Flask application
        app = create_app()

        # Start the server
        logger.info("Starting proxy server on port 3000")
        app.run(host='0.0.0.0', port=3001, debug=True)
    finally:
        # Clean up resources
        cleanup_cert_bundle()