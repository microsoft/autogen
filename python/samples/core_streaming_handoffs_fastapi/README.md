# AutoGen-Core Streaming Chat with Multi-Agent Handoffs via FastAPI

This sample demonstrates how to build a streaming chat API featuring multi-agent handoffs and persistent conversation history using `autogen-core` and FastAPI. For more details on the handoff pattern, see the [AutoGen documentation](https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/design-patterns/handoffs.html).

Inspired by `@ToryPan`'s example for streaming with Core API.

## Key Features

1.  **Streaming Response**: Implements real-time streaming of agent responses using FastAPI's `StreamingResponse`, `autogen-core`'s asynchronous features, and an `asyncio.Queue` to manage the data stream.
2.  **Multi-Agent Handoffs**: Showcases a system where different agents (Triage, Sales, Issues & Repairs) handle specific parts of a conversation, using tools (`delegate_tools`) to transfer the conversation between agents based on the context.
3.  **Persistent Multi-Turn Conversation**: Agents receive and process conversation history, enabling context-aware interactions. History is saved per conversation ID in JSON files within the `chat_history` directory, allowing conversations to resume across sessions.
4.  **Simple Web UI**: Includes a basic web interface (served via FastAPI's static files) for easy interaction with the chat system directly from a browser.

## File Structure

*   `app.py`: Main FastAPI application code, including API endpoints, agent definitions, runtime setup, handoff logic, and streaming.
*   `agent_user.py`: Defines the `UserAgent` responsible for interacting with the human user and saving chat history.
*   `agent_base.py`: Defines the base `AIAgent` class used by specialized agents.
*   `models.py`: Contains data models used for communication (e.g., `UserTask`, `AgentResponse`).
*   `topics.py`: Defines topic types used for routing messages between agents.
*   `tools.py`: Defines tools that agents can execute (e.g., `execute_order_tool`).
*   `tools_delegate.py`: Defines tools specifically for delegating/transferring the conversation to other agents.
*   `README.md`: (This document) Project introduction and usage instructions.
*   `static/`: Contains static files for the web UI (e.g., `index.html`).
*   `model_config_template.yaml`: Template for the model configuration file.

## Installation

First, ensure you have Python installed (recommended 3.8 or higher). Then, install the necessary libraries:

```bash
pip install "fastapi" "uvicorn[standard]" "autogen-core" "autogen-ext[openai]" "PyYAML"
```

## Configuration

Create a new file named `model_config.yaml` in the same directory as this README file to configure your language model settings (e.g., Azure OpenAI details). Use `model_config_template.yaml` as a starting point.

**Note**: For production, manage API keys securely using environment variables or other secrets management tools instead of hardcoding them in the configuration file.

## Running the Application

In the directory containing `app.py`, run the following command to start the FastAPI application:

```bash
uvicorn app:app --host 0.0.0.0 --port 8501 --reload
```

The application includes a simple web interface. After starting the server, navigate to `http://localhost:8501` in your browser.

The API endpoint for chat completions will be available at `http://localhost:8501/chat/completions`.

## Using the API

You can interact with the agent system by sending a POST request to the `/chat/completions` endpoint. The request body must be in JSON format and contain a `message` field (the user's input) and a `conversation_id` field to track the chat session.

**Request Body Format**:

```json
{
  "message": "I need refund for a product.",
  "conversation_id": "user123_session456"
}
```

**Example (using curl)**:

```bash
curl -N -X POST http://localhost:8501/chat/completions \
-H "Content-Type: application/json" \
-d '{
  "message": "Hi, I bought a rocket-powered unicycle and it exploded.",
  "conversation_id": "wile_e_coyote_1"
}'
```

**Example (using Python requests)**:

```python
import requests
import json
import uuid

url = "http://localhost:8501/chat/completions"
conversation_id = f"conv-id" # Generate a unique conversation ID for a different session.

def send_message(message_text):
    data = {
        'message': message_text,
        'conversation_id': conversation_id
    }
    headers = {'Content-Type': 'application/json'}
    try:
        print(f"\n>>> User: {message_text}")
        print("<<< Assistant: ", end="", flush=True)
        response = requests.post(url, json=data, headers=headers, stream=True)
        response.raise_for_status()
        full_response = ""
        for chunk in response.iter_content(chunk_size=None):
            if chunk:
                try:
                    # Decode the chunk
                    chunk_str = chunk.decode('utf-8')
                    # Handle potential multiple JSON objects in a single chunk
                    for line in chunk_str.strip().split('\n'):
                        if line:
                            data = json.loads(line)
                            # Check the new structure
                            if 'content' in data and isinstance(data['content'], dict) and 'message' in data['content']:
                                message_content = data['content']['message']
                                message_type = data['content'].get('type', 'string') # Default to string if type is missing

                                # Print based on type (optional, could just print message_content)
                                if message_type == 'function':
                                    print(f"[{message_type.upper()}] {message_content}", end='\n', flush=True) # Print function calls on new lines for clarity
                                    print("<<< Assistant: ", end="", flush=True) # Reprint prefix for next string part
                                else:
                                    print(message_content, end='', flush=True)

                                full_response += message_content # Append only the message part
                            else:
                                print(f"\nUnexpected chunk format: {line}")

                except json.JSONDecodeError:
                    print(f"\nError decoding chunk/line: '{line if 'line' in locals() else chunk_str}'")

        print("\n--- End of Response ---")
        return full_response

    except requests.exceptions.RequestException as e:
        print(f"\nError: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

# Start conversation
send_message("I want refund")
# Continue conversation (example)
# send_message("I want the rocket my friend Amith bought.")
# send_message("They are the SpaceX 3000s")
# send_message("That sounds great, I'll take it!")
# send_message("Yes, I agree to the price and the caveat.")


```