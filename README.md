# GigaChat API Proxy

This project provides a Flask-based API proxy for GigaChat that implements an OpenAI-compatible API interface. It uses the official GigaChat Python library to communicate with the GigaChat API while providing an interface that's compatible with OpenAI clients.

## Features

- OpenAI-compatible API endpoints for chat completions
- Support for streaming responses
- Support for function calling (tools) via OpenAI-compatible interface, even though the official GigaChat API uses a different format
- Proper SSL certificate handling for Russian certificates
- Token management for authentication with automatic token refresh using the GigaChat OAuth API (v2/oauth)
- Embeddings API support
- Models endpoint for compatibility
- Health check endpoint
- Configurable logging via environment variables

## Requirements

- Python 3.8+
- Flask 2.3+
- GigaChat Python library (version 0.1.15+)
- Other dependencies listed in requirements.txt

## Setup

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your GigaChat API credentials and optional logging configuration:
   ```
   # Required
   MASTER_TOKEN=your_gigachat_api_key

   # Optional logging configuration
   LOG_LEVEL=INFO           # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: DEBUG)
   LOG_USE_COLOR=true       # Options: true, false (default: true)
   LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s  # Custom log format
   ```
   The proxy will automatically use the MASTER_TOKEN to obtain and refresh access tokens via the GigaChat OAuth API (v2/oauth)
4. Make sure you have the required certificate files:
   - `russian_trusted_root_ca.cer` - Russian trusted root certificate
   - `combined_certs.pem` - Combined certificates (auto-generated)
   - `proxyman.pem` (if using Proxyman for debugging)

## Running the Application

You can start the Flask application using one of the following methods:

### Using run.py script
```
python run.py
```

### Using Docker

The application can be run using Docker, which simplifies deployment and ensures consistent environments.

#### Prerequisites
- Docker and Docker Compose installed on your system

#### Building and Running with Docker Compose

1. Make sure you have created the `.env` file with your GigaChat API credentials as described in the Setup section.

2. Build and start the Docker container:
   ```
   docker-compose up -d
   ```

3. To view logs:
   ```
   docker-compose logs -f
   ```

4. To stop the container:
   ```
   docker-compose down
   ```

#### Using the Docker Helper Script

A helper script `docker.sh` is provided to simplify Docker operations:

1. Make the script executable (if not already):
   ```
   chmod +x docker.sh
   ```

2. Use the script with various commands:
   ```
   ./docker.sh build    # Build the Docker image
   ./docker.sh start    # Start the container
   ./docker.sh stop     # Stop the container
   ./docker.sh restart  # Restart the container
   ./docker.sh logs     # View container logs
   ./docker.sh shell    # Open a shell in the running container
   ./docker.sh clean    # Remove container and image
   ./docker.sh help     # Show help message
   ```

#### Building and Running with Docker (without Docker Compose)

1. Build the Docker image:
   ```
   docker build -t gigachat-proxy .
   ```

2. Run the container:
   ```
   docker run -d -p 3001:3001 --env-file .env --name gigachat-proxy gigachat-proxy
   ```

3. To view logs:
   ```
   docker logs -f gigachat-proxy
   ```

4. To stop the container:
   ```
   docker stop gigachat-proxy
   ```

## API Usage

Health check endpoint:
```
curl http://localhost:3001/health
```

When started check if the token is valid:
```
curl http://localhost:3001/v1/models
```

