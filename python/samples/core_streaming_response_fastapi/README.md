# AutoGen-Core Streaming Chat API with FastAPI

This sample demonstrates how to build a streaming chat API with multi-turn conversation history using `autogen-core` and FastAPI.

## Key Features

1.  **Streaming Response**: Implements real-time streaming of LLM responses by utilizing FastAPI's `StreamingResponse`, `autogen-core`'s asynchronous features, and a global queue created with `asyncio.Queue()` to manage the data stream, thereby providing faster user-perceived response times.
2.  **Multi-Turn Conversation**: The Agent (`MyAgent`) can receive and process chat history records (`ChatHistory`) containing multiple turns of interaction, enabling context-aware continuous conversations.

## File Structure

*   `app.py`: FastAPI application code, including API endpoints, Agent definitions, runtime settings, and streaming logic.
*   `README.md`: (This document) Project introduction and usage instructions.

## Installation

First, make sure you have Python installed (recommended 3.8 or higher). Then, in your project directory, install the necessary libraries via pip:

```bash
pip install "fastapi" "uvicorn[standard]" "autogen-core" "autogen-ext[openai]"
```

## Configuration

**API Key**: In the `app.py` file, find the instantiation of `OpenAIChatCompletionClient` and replace `"YOUR_API_KEY_HERE"` with your actual OpenAI API key.

```python
# In the startup_event function of app.py
OpenAIChatCompletionClient(
    model="gemini-2.0-flash",  # Or other OpenAI style models
    api_key="YOUR_ACTUAL_API_KEY",  # Configure your API Key here
)
```

**Note**: Hardcoding API keys directly in the code is only suitable for local testing. For production environments, it is strongly recommended to use environment variables or other secure methods to manage keys.

## Running the Application

In the directory containing `app.py`, run the following command to start the FastAPI application:

```bash
uvicorn app:app --host 0.0.0.0 --port 8501 --reload
```

After the service starts, the API endpoint will be available at `http://<your-server-ip>:8501/chat/completions`.

## Using the API

You can interact with the Agent by sending a POST request to the `/chat/completions` endpoint. The request body must be in JSON format and contain a `messages` field, the value of which is a list, where each element represents a turn of conversation.

**Request Body Format**:

```json
{
  "messages": [
    {"source": "user", "content": "Hello!"},
    {"source": "assistant", "content": "Hello! How can I help you?"},
    {"source": "user", "content": "Introduce yourself."}
  ]
}
```

**Example (using curl)**:

```bash
curl -N -X POST http://localhost:8501/chat/completions \
-H "Content-Type: application/json" \
-d '{
  "messages": [
    {"source": "user", "content": "Hello, I'\''m Tory."},
    {"source": "assistant", "content": "Hello Tory, nice to meet you!"},
    {"source": "user", "content": "Say hello by my name and introduce yourself."}
  ]
}'
```

**Example (using Python requests)**:

```python
import requests
import json
url = "http://localhost:8501/chat/completions"
data = {
    'stream': True,
    'messages': [
            {'source': 'user', 'content': "Hello,I'm tory."},
            {'source': 'assistant', 'content':"hello Tory, nice to meet you!"},
            {'source': 'user', 'content': "Say hello by my name and introduce yourself."}
        ]
    }
headers = {'Content-Type': 'application/json'}
try:
    response = requests.post(url, json=data, headers=headers, stream=True)
    response.raise_for_status()
    for chunk in response.iter_content(chunk_size=None):
        if chunk:
            print(json.loads(chunk)["content"], end='', flush=True)

except requests.exceptions.RequestException as e:
    print(f"Error: {e}")
except json.JSONDecodeError as e:
    print(f"JSON Decode Error: {e}")
```

