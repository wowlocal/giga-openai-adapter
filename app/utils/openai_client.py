from openai import OpenAI
from app.auth.token_manager import token_manager
from app.utils.ssl import create_http_client
from app.config import GIGACHAT_API_V1_URL, logger

def create_openai_client():
    """Create an OpenAI client configured for GigaChat API"""
    try:
        # Get a valid token
        token = token_manager.get_valid_token()

        # Create HTTP client with proper SSL verification
        http_client = create_http_client()

        # Initialize OpenAI client
        client = OpenAI(
            api_key=token,
            base_url=GIGACHAT_API_V1_URL,
            http_client=http_client
        )

        logger.info("Created OpenAI client for GigaChat API")
        return client

    except Exception as e:
        logger.error(f"Error creating OpenAI client: {str(e)}", exc_info=True)
        raise

# Create a function to get a client with a fresh token
def get_client():
    """Get an OpenAI client with a fresh token"""
    return create_openai_client()