# Azure OpenAI with AAD Auth

This guide will show you how to use the Azure OpenAI client with Azure Active Directory (AAD) authentication.

The identity used must be assigned the [**Cognitive Services OpenAI User**](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/role-based-access-control#cognitive-services-openai-user) role.

## Install Azure Identity client

The Azure identity client is used to authenticate with Azure Active Directory.

```sh
pip install azure-identity
```

## Using the Model Client

```python
from autogen_ext.models import AzureOpenAIChatCompletionClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider

# Create the token provider
token_provider = get_bearer_token_provider(
    DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
)

client = AzureOpenAIChatCompletionClient(
    model="{your-azure-deployment}",
    api_version="2024-02-01",
    azure_endpoint="https://{your-custom-endpoint}.openai.azure.com/",
    azure_ad_token_provider=token_provider,
    model_capabilities={
        "vision":True,
        "function_calling":True,
        "json_output":True,
    }
)
```

```{note}
See [here](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/managed-identity#chat-completions) for how to use the Azure client directly or for more info.
```
