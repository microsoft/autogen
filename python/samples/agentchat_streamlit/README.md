# Streamlit AgentChat Sample Application

This is a sample AI chat assistant built with [Streamlit](https://streamlit.io/)

## Setup

Install the `streamlit` package with the following command:

```bash
pip install streamlit
```

To use Azure OpenAI models or models hosted on OpenAI-compatible API endpoints,
you need to install the `autogen-ext[openai,azure]` package. You can install it with the following command:

```bash
pip install "autogen-ext[openai,azure]"
# pip install "autogen-ext[openai]" for OpenAI models
```

Create a new file named `model_config.yml` in the the same directory as the script
to configure the model you want to use.

For example, to use `gpt-4o-mini` model from Azure OpenAI, you can use the following configuration:

```yml
provider: autogen_ext.models.openai.AzureOpenAIChatCompletionClient
config:
  azure_deployment: "gpt-4o-mini"
  model: gpt-4o-mini
  api_version: REPLACE_WITH_MODEL_API_VERSION
  azure_endpoint: REPLACE_WITH_MODEL_ENDPOINT
  api_key: REPLACE_WITH_MODEL_API_KEY
```

For more information on how to configure the model and use other providers,
please refer to the [Models documentation](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/models.html).

## Run

Run the following command to start the web application:

```bash
streamlit run main.py
```