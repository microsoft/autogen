# Agent Backed by OpenAI Assistant API

The GPTAssistantAgent is a powerful component of the AutoGen framework, utilizing OpenAI's Assistant API to enhance agents with advanced capabilities. This agent enables the integration of multiple tools such as the Code Interpreter, File Search, and Function Calling, allowing for a highly customizable and dynamic interaction model.

Version Requirements:

- AutoGen: Version 0.2.27 or higher.
- OpenAI: Version 1.21 or higher.

Key Features of the GPTAssistantAgent:

- Multi-Tool Mastery:  Agents can leverage a combination of OpenAI's built-in tools, like [Code Interpreter](https://platform.openai.com/docs/assistants/tools/code-interpreter) and [File Search](https://platform.openai.com/docs/assistants/tools/file-search), alongside custom tools you create or integrate via [Function Calling](https://platform.openai.com/docs/assistants/tools/function-calling).

- Streamlined Conversation Management:  Benefit from persistent threads that automatically store message history and adjust based on the model's context length. This simplifies development by allowing you to focus on adding new messages rather than managing conversation flow.

- File Access and Integration:  Enable agents to access and utilize files in various formats. Files can be incorporated during agent creation or throughout conversations via threads. Additionally, agents can generate files (e.g., images, spreadsheets) and cite referenced files within their responses.

For a practical illustration, here are some examples:

- [Chat with OpenAI Assistant using function call](/docs/notebooks/agentchat_oai_assistant_function_call) demonstrates how to leverage function calling to enable intelligent function selection.
- [GPTAssistant with Code Interpreter](/docs/notebooks/agentchat_oai_code_interpreter) showcases the integration of the  Code Interpreter tool which executes Python code dynamically within applications.
- [Group Chat with GPTAssistantAgent](/docs/notebooks/agentchat_oai_assistant_groupchat) demonstrates how to use the GPTAssistantAgent in AutoGen's group chat mode, enabling collaborative task performance through automated chat with agents powered by LLMs, tools, or humans.

## Create a OpenAI Assistant in Autogen

```python
import os

from autogen import config_list_from_json
from autogen.agentchat.contrib.gpt_assistant_agent import GPTAssistantAgent

assistant_id = os.environ.get("ASSISTANT_ID", None)
config_list = config_list_from_json("OAI_CONFIG_LIST")
llm_config = {
    "config_list": config_list,
}
assistant_config = {
    # define the openai assistant behavior as you need
}
oai_agent = GPTAssistantAgent(
    name="oai_agent",
    instructions="I'm an openai assistant running in autogen",
    llm_config=llm_config,
    assistant_config=assistant_config,
)
```

## Use OpenAI Assistant Built-in Tools and Function Calling

### Code Interpreter

The [Code Interpreter](https://platform.openai.com/docs/assistants/tools/code-interpreter) empowers your agents to write and execute Python code in a secure environment provide by OpenAI. This unlocks several capabilities, including but not limited to:

- Process data: Handle various data formats and manipulate data on the fly.
- Generate outputs: Create new data files or even visualizations like graphs.
- ...

Using the Code Interpreter with the following configuration.
```python
assistant_config = {
    "tools": [
        {"type": "code_interpreter"},
    ],
    "tool_resources": {
        "code_interpreter": {
            "file_ids": ["$file.id"]  # optional. Files that are passed at the Assistant level are accessible by all Runs with this Assistant.
        }
    }
}
```

To get the `file.id`, you can employ two methods:

1. OpenAI Playground: Leverage the OpenAI Playground, an interactive platform accessible at https://platform.openai.com/playground, to upload your files and obtain the corresponding file IDs.

2. Code-Based Uploading: Alternatively, you can upload files and retrieve their file IDs programmatically using the following code snippet:

    ```python
    from openai import OpenAI
    client = OpenAI(
        # Defaults to os.environ.get("OPENAI_API_KEY")
    )
    # Upload a file with an "assistants" purpose
    file = client.files.create(
      file=open("mydata.csv", "rb"),
      purpose='assistants'
    )
    ```

### File Search

The [File Search](https://platform.openai.com/docs/assistants/tools/file-search) tool empowers your agents to tap into knowledge beyond its pre-trained model. This allows you to incorporate your own documents and data, such as product information or code files, into your agent's capabilities.

Using the File Search with the following configuration.

```python
assistant_config = {
    "tools": [
        {"type": "file_search"},
    ],
    "tool_resources": {
        "file_search": {
            "vector_store_ids": ["$vector_store.id"]
        }
    }
}
```

Here's how to obtain the vector_store.id using two methods:

1. OpenAI Playground: Leverage the OpenAI Playground, an interactive platform accessible at https://platform.openai.com/playground, to create a vector store, upload your files, and add it into your vector store. Once complete, you'll be able to retrieve the associated `vector_store.id`.

2. Code-Based Uploading:Alternatively, you can upload files and retrieve their file IDs programmatically using the following code snippet:

    ```python
    from openai import OpenAI
    client = OpenAI(
        # Defaults to os.environ.get("OPENAI_API_KEY")
    )

    # Step 1: Create a Vector Store
    vector_store = client.beta.vector_stores.create(name="Financial Statements")
    print("Vector Store created:", vector_store.id)  # This is your vector_store.id

    # Step 2: Prepare Files for Upload
    file_paths = ["edgar/goog-10k.pdf", "edgar/brka-10k.txt"]
    file_streams = [open(path, "rb") for path in file_paths]

    # Step 3: Upload Files and Add to Vector Store (with status polling)
    file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vector_store.id, files=file_streams
    )

    # Step 4: Verify Completion (Optional)
    print("File batch status:", file_batch.status)
    print("Uploaded file count:", file_batch.file_counts.processed)
    ```

### Function calling

Function Calling empowers you to extend the capabilities of your agents with your pre-defined functionalities, which allows you to describe custom functions to the Assistant, enabling intelligent function selection and argument generation.

Using the Function calling with the following configuration.

```python
# learn more from https://platform.openai.com/docs/guides/function-calling/function-calling
from autogen.function_utils import get_function_schema

def get_current_weather(location: str) -> dict:
    """
    Retrieves the current weather for a specified location.

    Args:
    location (str): The location to get the weather for.

    Returns:
    Union[str, dict]: A dictionary with weather details..
    """

    # Simulated response
    return {
        "location": location,
        "temperature": 22.5,
        "description": "Partly cloudy"
    }

api_schema = get_function_schema(
    get_current_weather,
    name=get_current_weather.__name__,
    description="Returns the current weather data for a specified location."
)

assistant_config = {
    "tools": [
        {
            "type": "function",
            "function": api_schema,
        }
    ],
}
```
