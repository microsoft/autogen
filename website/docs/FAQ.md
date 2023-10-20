# Frequently Asked Questions

## Set your API endpoints

There are multiple ways to construct a list of configurations for LLM inference.

### Option 1: Load a list of endpoints from json

The [`config_list_from_json`](/docs/reference/oai/openai_utils#config_list_from_json) function loads a list of configurations from an environment variable or a json file.

For example,

```python
import autogen
config_list = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
    file_location=".",
    filter_dict={
        "model": {
            "gpt-4",
            "gpt-3.5-turbo",
        }
    }
)
```

It first looks for environment variable "OAI_CONFIG_LIST" which needs to be a valid json string. If that variable is not found, it then looks for a json file named "OAI_CONFIG_LIST" under the specified `file_location`. It then filters the configs by models (you can filter by other keys as well).

The `OAI_CONFIG_LIST` var or file content looks like the following:
```json
[
    {
        "model": "gpt-4",
        "api_key": "<your OpenAI API key here>"
    },
    {
        "model": "gpt-4",
        "api_key": "<your Azure OpenAI API key here>",
        "api_base": "<your Azure OpenAI API base here>",
        "api_type": "azure",
        "api_version": "2023-07-01-preview"
    },
    {
        "model": "gpt-3.5-turbo",
        "api_key": "<your Azure OpenAI API key here>",
        "api_base": "<your Azure OpenAI API base here>",
        "api_type": "azure",
        "api_version": "2023-07-01-preview"
    }
]
```

### Option 2: Construct a list of endpoints for OpenAI or Azure OpenAI

The [`config_list_from_models`](/docs/reference/oai/openai_utils#config_list_from_models) function tries to create a list of configurations using Azure OpenAI endpoints and OpenAI endpoints for the provided list of models. It assumes the api keys and api bases are stored in the corresponding environment variables or local txt files:

- OpenAI API key: os.environ["OPENAI_API_KEY"] or `openai_api_key_file="key_openai.txt"`.
- Azure OpenAI API key: os.environ["AZURE_OPENAI_API_KEY"] or `aoai_api_key_file="key_aoai.txt"`. Multiple keys can be stored, one per line.
- Azure OpenAI API base: os.environ["AZURE_OPENAI_API_BASE"] or `aoai_api_base_file="base_aoai.txt"`. Multiple bases can be stored, one per line.

It's OK to have only the OpenAI API key, or only the Azure OpenAI API key + base.

```python
import autogen
config_list = autogen.config_list_from_models(model_list=["gpt-4", "gpt-3.5-turbo", "gpt-3.5-turbo-16k"])
```

> For Azure the model name refers to the OpenAI Studio deployment name.

The config list looks like the following, if only OpenAI API key is available:
```python
config_list = [
    {
        'model': 'gpt-4',
        'api_key': '<your OpenAI API key here>',
    },  # OpenAI API endpoint for gpt-4
    {
        'model': 'gpt-3.5-turbo',
        'api_key': '<your OpenAI API key here>',
    },  # OpenAI API endpoint for gpt-3.5-turbo
    {
        'model': 'gpt-3.5-turbo-16k',
        'api_key': '<your OpenAI API key here>',
    },  # OpenAI API endpoint for gpt-3.5-turbo-16k
]
```

### Use the constructed configuration list in agents

Make sure the "config_list" is included in the `llm_config` in the constructor of the LLM-based agent. For example,
```python
assistant = autogen.AssistantAgent(
    name="assistant",
    llm_config={"config_list": config_list}
)
```

The `llm_config` is used in the [`create`](/docs/reference/oai/completion#create) function for LLM inference.
When `llm_config` is not provided, the agent will rely on other openai settings such as `openai.api_key` or the environment variable `OPENAI_API_KEY`, which can also work when you'd like to use a single endpoint.
You can also explicitly specify that by:
```python
assistant = autogen.AssistantAgent(name="assistant", llm_config={"api_key": ...})
```

### Can I use non-OpenAI models?

Yes. Please check https://microsoft.github.io/autogen/blog/2023/07/14/Local-LLMs for an example.

## Handle Rate Limit Error and Timeout Error

You can set `retry_wait_time` and `max_retry_period` to handle rate limit error. And you can set `request_timeout` to handle timeout error. They can all be specified in `llm_config` for an agent, which will be used in the [`create`](/docs/reference/oai/completion#create) function for LLM inference.

- `retry_wait_time` (int): the time interval to wait (in seconds) before retrying a failed request.
- `max_retry_period` (int): the total timeout (in seconds) allowed for retrying failed requests.
- `request_timeout` (int): the timeout (in seconds) sent with a single request.

Please refer to the [documentation](/docs/Use-Cases/enhanced_inference#runtime-error) for more info.

## How to continue a finished conversation

When you call `initiate_chat` the conversation restarts by default. You can use `send` or `initiate_chat(clear_history=False)` to continue the conversation.

## How do we decide what LLM is used for each agent? How many agents can be used? How do we decide how many agents in the group?

Each agent can be customized. You can use LLMs, tools or human behind each agent. If you use an LLM for an agent, use the one best suited for its role. There is no limit of the number of agents, but start from a small number like 2, 3. The more capable is the LLM and the fewer roles you need, the fewer agents you need.

The default user proxy agent doesn't use LLM. If you'd like to use an LLM in UserProxyAgent, the use case could be to simulate user's behavior.

The default assistant agent is instructed to use both coding and language skills. It doesn't have to do coding, depending on the tasks. And you can customize the system message. So if you want to use it for coding, use a model that's good at coding.

## Why is code not saved as file?

If you are using a custom system message for the coding agent, please include something like:
`If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line.`
in the system message. This line is in the default system message of the `AssistantAgent`.

If the `# filename` doesn't appear in the suggested code still, consider adding explicit instructions such as "save the code to disk" in the initial user message in `initiate_chat`.
The `AssistantAgent` doesn't save all the code by default, because there are cases in which one would just like to finish a task without saving the code.

## Code execution

We strongly recommend using docker to execute code. There are two ways to use docker:

1. Run autogen in a docker container. For example, when developing in GitHub codespace, the autogen runs in a docker container.
2. Run autogen outside of a docker, while perform code execution with a docker container. For this option, make sure the python package `docker` is installed. When it is not installed and `use_docker` is omitted in `code_execution_config`, the code will be executed locally (this behavior is subject to change in future).

### Enable Python 3 docker image

You might want to override the default docker image used for code execution. To do that set `use_docker` key of `code_execution_config` property to the name of the image. E.g.:
```python
user_proxy = autogen.UserProxyAgent(
    name="agent",
    human_input_mode="TERMINATE",
    max_consecutive_auto_reply=10,
    code_execution_config={"work_dir":"_output", "use_docker":"python:3"},
    llm_config=llm_config,
    system_message=""""Reply TERMINATE if the task has been solved at full satisfaction.
Otherwise, reply CONTINUE, or the reason why the task is not solved yet."""
)
```

If you have problems with agents running `pip install` or get errors similar to `Error while fetching server API version: ('Connection aborted.', FileNotFoundError(2, 'No such file or directory')`, you can choose **'python:3'** as image as shown in the code example above and that should solve the problem.
