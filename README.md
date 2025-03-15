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
3. Create a `.env` file with your GigaChat API credentials:
   ```
   MASTER_TOKEN=your_gigachat_api_key
   ```
   The proxy will automatically use the MASTER_TOKEN to obtain and refresh access tokens via the GigaChat OAuth API (v2/oauth)
4. Make sure you have the required certificate files:
   - `russian_trusted_root_ca.cer` - Russian trusted root certificate
   - `combined_certs.pem` - Combined certificates (auto-generated)
   - `proxyman.pem` (if using Proxyman for debugging)

## Running the Application

You can start the Flask application using one of the following methods:

### Using run.py script