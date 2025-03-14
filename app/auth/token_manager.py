import time
import uuid
from app.config import MASTER_TOKEN, GIGACHAT_OAUTH_URL, logger
from app.utils.ssl import create_http_client

class TokenManager:
    """Manages authentication tokens for the GigaChat API"""

    def __init__(self, master_token=None):
        """Initialize the token manager with a master token"""
        self.master_token = master_token or MASTER_TOKEN
        self.access_token = None
        self.expires_at = None
        self.http_client = create_http_client()

    def get_valid_token(self):
        """Get a valid token, refreshing if necessary"""
        if not self.access_token or not self.expires_at or time.time() * 1000 >= self.expires_at:
            logger.info("Token expired or not set, refreshing...")
            self.refresh_token()
        return self.access_token

    def refresh_token(self):
        """Get new access token from Sberbank OAuth endpoint"""
        try:
            # Encode master token in base64 for Basic auth
            auth_string = f"Basic {self.master_token}"

            # Prepare headers
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json',
                'RqUID': str(uuid.uuid4()),
                'Authorization': auth_string
            }

            # Prepare data
            data = {
                'scope': 'GIGACHAT_API_PERS'
            }

            # Make request to OAuth endpoint using our configured http_client with proper SSL verification
            response = self.http_client.post(
                GIGACHAT_OAUTH_URL,
                headers=headers,
                data=data
            )
            response.raise_for_status()

            # Parse response
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.expires_at = token_data['expires_at']
            logger.info("Successfully obtained new access token")
            return self.access_token

        except Exception as e:
            logger.error(f"Error getting access token: {str(e)}", exc_info=True)
            raise

# Create a singleton instance of the token manager
token_manager = TokenManager()