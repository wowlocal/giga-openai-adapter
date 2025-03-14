import os
import certifi
import httpx
from app.config import CUSTOM_CERT_PATH, PROXYMAN_CERT_PATH, COMBINED_CERT_PATH, logger

def create_combined_cert_bundle():
    """
    Create a custom certificate bundle by combining system certs with custom certs.
    This approach is more secure than disabling SSL verification entirely.
    """
    try:
        # Get the system certificate bundle
        custom_ca_bundle = certifi.where()
        with open(custom_ca_bundle, 'rb') as ca_bundle:
            ca_bundle_content = ca_bundle.read()

        # Read custom certificates
        with open(CUSTOM_CERT_PATH, 'rb') as custom_cert:
            custom_cert_content = custom_cert.read()

        with open(PROXYMAN_CERT_PATH, 'rb') as proxyman_cert:
            proxyman_cert_content = proxyman_cert.read()

        # Create a temporary combined cert file
        with open(COMBINED_CERT_PATH, 'wb') as combined_cert:
            combined_cert.write(ca_bundle_content)
            combined_cert.write(b'\n')
            combined_cert.write(custom_cert_content)
            combined_cert.write(b'\n')
            combined_cert.write(proxyman_cert_content)

        logger.info(f"Created combined certificate bundle at {COMBINED_CERT_PATH}")
        return COMBINED_CERT_PATH

    except Exception as e:
        logger.error(f"Error creating combined certificate bundle: {str(e)}", exc_info=True)
        raise

def create_http_client():
    """Create an HTTP client with proper SSL verification"""
    try:
        # Create the combined certificate bundle
        cert_path = create_combined_cert_bundle()

        # Create and return the HTTP client
        ssl_context = httpx.create_ssl_context(verify=cert_path)
        http_client = httpx.Client(verify=cert_path)

        logger.info("Created HTTP client with custom SSL verification")
        return http_client

    except Exception as e:
        logger.error(f"Error creating HTTP client: {str(e)}", exc_info=True)
        raise

def cleanup_cert_bundle():
    """Clean up the temporary combined certificate file"""
    if os.path.exists(COMBINED_CERT_PATH):
        try:
            os.remove(COMBINED_CERT_PATH)
            logger.info(f"Removed temporary certificate file: {COMBINED_CERT_PATH}")
        except Exception as e:
            logger.error(f"Failed to remove temporary certificate file: {str(e)}")