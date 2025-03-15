from app.config import logger

# Test different log levels
logger.debug("This is a DEBUG message")
logger.info("This is an INFO message")
logger.warning("This is a WARNING message")
logger.error("This is an ERROR message")
logger.critical("This is a CRITICAL message")

# Test the specific warning for unexpected finish_reason
logger.warning("[PROXY] Unexpected finish_reason value: 'unknown_reason'. Expected one of: ['stop', 'length', 'tool_calls', 'content_filter', None]")