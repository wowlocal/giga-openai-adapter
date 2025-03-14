import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get master token from environment variable
MASTER_TOKEN = os.getenv('MASTER_TOKEN')
if not MASTER_TOKEN:
    raise ValueError("MASTER_TOKEN environment variable is not set")

# API configuration
GIGACHAT_BASE_URL = "https://gigachat.devices.sberbank.ru"
GIGACHAT_API_V1_URL = f"{GIGACHAT_BASE_URL}/api/v1"
GIGACHAT_OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"

# Get the current directory for certificate paths
current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CUSTOM_CERT_PATH = os.path.join(current_dir, "russian_trusted_root_ca.cer")
PROXYMAN_CERT_PATH = os.path.join(current_dir, "proxyman.pem")
COMBINED_CERT_PATH = os.path.join(current_dir, "combined_certs.pem")

# Check if the custom certificate files exist
if not os.path.exists(CUSTOM_CERT_PATH):
    raise FileNotFoundError(f"Custom certificate file not found: {CUSTOM_CERT_PATH}")
if not os.path.exists(PROXYMAN_CERT_PATH):
    raise FileNotFoundError(f"Proxyman certificate file not found: {PROXYMAN_CERT_PATH}")