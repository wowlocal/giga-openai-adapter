from gigachat import GigaChat
from app.auth.token_manager import token_manager
from app.utils.ssl import create_combined_cert_bundle
from app.config import GIGACHAT_API_V1_URL, logger
import os

def create_gigachat_client():
    """Create a GigaChat client"""
    try:
        # Get a valid token
        token = token_manager.get_valid_token()

        # key = os.getenv("MASTER_TOKEN")

        # Get the combined certificate path
        cert_path = create_combined_cert_bundle()

        # Initialize GigaChat client
        client = GigaChat(
            # credentials=key,
            access_token=token,
            ca_bundle_file=cert_path,
            base_url=GIGACHAT_API_V1_URL,
            verify_ssl_certs=False  # Disable SSL verification for compatibility
        )

        logger.info("Created GigaChat client")
        return client

    except Exception as e:
        logger.error(f"Error creating GigaChat client: {str(e)}", exc_info=True)
        raise

# Create a function to get a client with a fresh token
def get_client():
    """Get a GigaChat client with a fresh token"""
    return create_gigachat_client()