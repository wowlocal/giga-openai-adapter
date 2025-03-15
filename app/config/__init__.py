import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ANSI color codes
class ColorFormatter(logging.Formatter):
    """
    Custom formatter to add colors to log messages based on their level.
    """
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[94m',  # Blue
        'INFO': '',           # Normal (no color)
        'WARNING': '\033[93m', # Yellow
        'ERROR': '\033[91m',  # Red
        'CRITICAL': '\033[91m\033[1m',  # Bold Red
        'RESET': '\033[0m'    # Reset
    }

    def format(self, record):
        # Save the original format
        format_orig = self._style._fmt

        # Add color based on the log level
        if record.levelname in self.COLORS:
            self._style._fmt = f"{self.COLORS[record.levelname]}%(asctime)s - %(name)s - %(levelname)s - %(message)s{self.COLORS['RESET']}"

        # Call the original formatter
        result = logging.Formatter.format(self, record)

        # Restore the original format
        self._style._fmt = format_orig

        return result

# Configure logging - first remove any existing handlers to avoid duplicates
logging.root.handlers = []

# Create and configure the handler with our color formatter
handler = logging.StreamHandler()
handler.setFormatter(ColorFormatter(fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Configure root logger
logging.root.setLevel(logging.DEBUG)
logging.root.addHandler(handler)

# Get our module's logger
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