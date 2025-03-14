# GigaChat API Proxy

This project provides a Flask-based API proxy for GigaChat that implements an OpenAI-compatible API interface. It has been refactored to use the official GigaChat Python library instead of the OpenAI library.

## Features

- OpenAI-compatible API endpoints for chat completions
- Support for streaming responses
- Support for function calling (tools)
- Proper SSL certificate handling for Russian certificates
- Token management for authentication

## Requirements

- Python 3.8+
- Flask
- GigaChat Python library
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
   - `proxyman.pem` (if using Proxyman for debugging)

## Running the Application

Start the Flask application:

```
python app/__init__.py
```

## Testing

You can run the test script to verify the GigaChat integration:

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

The API implements an OpenAI-compatible interface. You can use it with any OpenAI client by changing the base URL.

Example request:

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