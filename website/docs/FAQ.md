# Frequently Asked Questions

## Set your API endpoints

There are multiple ways to construct a list of configurations for LLM inference.

### Load a list of endpoints from json

The [`config_list_from_json`](/docs/reference/autogen/oai/openai_utils#config_list_from_json) function loads a list of configurations from an environment variable or a json file.

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
    },
]
```

### Construct a list of endpoints for OpenAI or Azure OpenAI

he [`config_list_from_models`](/docs/reference/autogen/oai/openai_utils#config_list_from_models) function tries to create a list of configurations using Azure OpenAI endpoints and OpenAI endpoints for the provided list of models. It assumes the api keys and api bases are stored in the corresponding environment variables or local txt files:

- OpenAI API key: os.environ["OPENAI_API_KEY"] or `openai_api_key_file="key_openai.txt"`.
- Azure OpenAI API key: os.environ["AZURE_OPENAI_API_KEY"] or `aoai_api_key_file="key_aoai.txt"`. Multiple keys can be stored, one per line.
- Azure OpenAI API base: os.environ["AZURE_OPENAI_API_BASE"] or `aoai_api_base_file="base_aoai.txt"`. Multiple bases can be stored, one per line.

It's OK to have only the OpenAI API key, or only the Azure OpenAI API key + base.

```python
import autogen
config_list = autogen.config_list_from_models(model_list=["gpt-4", "gpt-3.5-turbo", "gpt-3.5-turbo-16k"])
```

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
