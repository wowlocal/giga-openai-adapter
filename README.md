# GigaChat API Proxy

This project provides a Flask-based API proxy for GigaChat that implements an OpenAI-compatible API interface. It uses the official GigaChat Python library to communicate with the GigaChat API while providing an interface that's compatible with OpenAI clients.

## Features

- OpenAI-compatible API endpoints for chat completions
- Support for streaming responses
- Support for function calling (tools)
- Proper SSL certificate handling for Russian certificates
- Token management for authentication
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

This will start the server on port 3001 with debug mode enabled.

### Using run.sh shell script

```
./run.sh
```

## Project Structure

```
/
├── app/                    # Main application package
│   ├── api/                # API endpoints
│   │   ├── chat.py         # Chat completions endpoint
│   │   ├── embeddings.py   # Embeddings endpoint
│   │   ├── general.py      # General endpoints
│   │   ├── health.py       # Health check endpoint
│   │   └── models.py       # Models endpoint
│   ├── auth/               # Authentication utilities
│   ├── config/             # Configuration utilities
│   ├── utils/              # Utility functions
│   └── __init__.py         # App initialization
├── tests/                  # Test directory
├── giga_test.py            # GigaChat API test script
├── run.py                  # Main script to run the app
├── run.sh                  # Shell script to run the app
├── run_tests.py            # Script to run tests
├── run_tests.sh            # Shell script to run tests
├── requirements.txt        # Project dependencies
└── README.md               # Project documentation
```

## Testing

You can test the application using the provided test scripts:

### Using run_tests.py

```
python run_tests.py
```

### Using run_tests.sh

```
./run_tests.sh
```

### Running specific tests

To test the GigaChat integration specifically:

```
python giga_test.py
```

This will run several tests:
- Basic chat completion
- Streaming responses
- Function calling
- Multiple functions
- Embeddings

## API Usage

The API implements an OpenAI-compatible interface. You can use it with any OpenAI client by changing the base URL to point to your instance of the proxy.

### Available Endpoints

- `/v1/chat/completions` - Chat completions API
- `/v1/embeddings` - Embeddings API
- `/v1/models` - Models API
- `/health` - Health check endpoint

### Example Request: Chat Completions

```json
POST /v1/chat/completions
{
  "model": "GigaChat",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello, how are you?"}
  ],
  "temperature": 0.7,
  "max_tokens": 100
}
```

## Function Calling

The API supports function calling (tools) in the same format as OpenAI:

```json
POST /v1/chat/completions
{
  "model": "GigaChat",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What's the weather in Moscow?"}
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get the current weather in a location",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "The city and state, e.g. San Francisco, CA"
            }
          },
          "required": ["location"]
        }
      }
    }
  ]
}
```

## License

MIT