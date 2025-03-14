# GigaChat API Proxy

A modular Flask application that serves as a proxy for the GigaChat API, providing OpenAI-compatible endpoints.

## Features

- OpenAI-compatible API endpoints
- Token management for authentication
- SSL certificate handling for secure communication
- Support for streaming and non-streaming chat completions
- Support for embeddings
- General proxy for other GigaChat API endpoints

## Project Structure

```
.
├── app/                    # Main application package
│   ├── __init__.py         # Application factory
│   ├── api/                # API endpoints
│   │   ├── __init__.py
│   │   ├── chat.py         # Chat completions endpoint
│   │   ├── embeddings.py   # Embeddings endpoint
│   │   ├── general.py      # General proxy endpoint
│   │   └── models.py       # Models endpoint
│   ├── auth/               # Authentication
│   │   ├── __init__.py
│   │   └── token_manager.py # Token management
│   ├── config/             # Configuration
│   │   └── __init__.py     # Configuration settings
│   └── utils/              # Utility functions
│       ├── __init__.py
│       ├── error_handlers.py # Error handlers
│       ├── helpers.py      # Helper functions
│       ├── openai_client.py # OpenAI client
│       └── ssl.py          # SSL certificate handling
├── run.py                  # Application entry point
├── russian_trusted_root_ca.cer # Custom certificate
└── proxyman.pem            # Proxyman certificate
```

## Setup

1. Create a `.env` file in the root directory with the following content:
   ```
   MASTER_TOKEN=your_master_token
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   ```
   python run.py
   ```

## API Endpoints

- `/v1/models` - List available models
- `/v1/chat/completions` - Chat completions
- `/v1/embeddings` - Embeddings
- `/<path:path>` - General proxy for other GigaChat API endpoints

## Requirements

- Python 3.7+
- Flask
- OpenAI Python SDK
- HTTPX
- Certifi
- python-dotenv