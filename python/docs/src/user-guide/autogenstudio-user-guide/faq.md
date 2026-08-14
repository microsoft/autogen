---
myst:
  html_meta:
    "description lang=en": |
      FAQ for AutoGen Studio - A low code tool for building and debugging multi-agent systems
---

# FAQ

## Q: How do I specify the directory where files(e.g. database) are stored?

A: You can specify the directory where files are stored by setting the `--appdir` argument when running the application. For example, `autogenstudio ui --appdir /path/to/folder`. This will store the database (default) and other files in the specified directory e.g. `/path/to/folder/database.sqlite`.

## Q: Can I use other models with AutoGen Studio?

Yes. AutoGen standardizes on the openai model api format, and you can use any api server that offers an openai compliant endpoint.

AutoGen Studio is based on declaritive specifications which applies to models as well. Agents can include a model_client field which specifies the model endpoint details including `model`, `api_key`, `base_url`, `model type`. Note, you can define your [model client](https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/components/model-clients.html) in python and dump it to a json file for use in AutoGen Studio.

In the following sample, we will define an OpenAI, AzureOpenAI and a local model client in python and dump them to a json file.

```python
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient, OpenAIChatCompletionClient
from autogen_ext.models.anthropic import AnthropicChatCompletionClient
from autogen_core.models import ModelInfo

model_client=OpenAIChatCompletionClient(
            model="gpt-4o-mini",
        )
print(model_client.dump_component().model_dump_json())


az_model_client = AzureOpenAIChatCompletionClient(
    azure_deployment="{your-azure-deployment}",
    model="gpt-4o",
    api_version="2024-06-01",
    azure_endpoint="https://{your-custom-endpoint}.openai.azure.com/",
    api_key="sk-...",
)
print(az_model_client.dump_component().model_dump_json())

anthropic_client = AnthropicChatCompletionClient(
        model="claude-3-sonnet-20240229",
        api_key="your-api-key",  # Optional if ANTHROPIC_API_KEY is set in environment
    )
print(anthropic_client.dump_component().model_dump_json())

mistral_vllm_model = OpenAIChatCompletionClient(
        model="TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
        base_url="http://localhost:1234/v1",
        model_info=ModelInfo(vision=False, function_calling=True, json_output=False, family="unknown", structured_output=True),
    )
print(mistral_vllm_model.dump_component().model_dump_json())
```

OpenAI

```json
{
  "provider": "autogen_ext.models.openai.OpenAIChatCompletionClient",
  "component_type": "model",
  "version": 1,
  "component_version": 1,
  "description": "Chat completion client for OpenAI hosted models.",
  "label": "OpenAIChatCompletionClient",
  "config": { "model": "gpt-4o-mini" }
}
```

Azure OpenAI

```json
{
  "provider": "autogen_ext.models.openai.AzureOpenAIChatCompletionClient",
  "component_type": "model",
  "version": 1,
  "component_version": 1,
  "description": "Chat completion client for Azure OpenAI hosted models.",
  "label": "AzureOpenAIChatCompletionClient",
  "config": {
    "model": "gpt-4o",
    "api_key": "sk-...",
    "azure_endpoint": "https://{your-custom-endpoint}.openai.azure.com/",
    "azure_deployment": "{your-azure-deployment}",
    "api_version": "2024-06-01"
  }
}
```

Anthropic

```json
{
  "provider": "autogen_ext.models.anthropic.AnthropicChatCompletionClient",
  "component_type": "model",
  "version": 1,
  "component_version": 1,
  "description": "Chat completion client for Anthropic's Claude models.",
  "label": "AnthropicChatCompletionClient",
  "config": {
    "model": "claude-3-sonnet-20240229",
    "max_tokens": 4096,
    "temperature": 1.0,
    "api_key": "your-api-key"
  }
}
```

Have a local model server like Ollama, vLLM or LMStudio that provide an OpenAI compliant endpoint? You can use that as well.

```json
{
  "provider": "autogen_ext.models.openai.OpenAIChatCompletionClient",
  "component_type": "model",
  "version": 1,
  "component_version": 1,
  "description": "Chat completion client for OpenAI hosted models.",
  "label": "OpenAIChatCompletionClient",
  "config": {
    "model": "TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
    "model_info": {
      "vision": false,
      "function_calling": true,
      "json_output": false,
      "family": "unknown",
      "structured_output": true
    },
    "base_url": "http://localhost:1234/v1"
  }
}
```

```{caution}
It is important that you add the `model_info` field to the model client specification for custom models. This is used by the framework instantiate and use the model correctly. Also, the `AssistantAgent` and many other agents in AgentChat require the model to have the `function_calling` capability.
```

## Q: The server starts but I can't access the UI

A: If you are running the server on a remote machine (or a local machine that fails to resolve localhost correctly), you may need to specify the host address. By default, the host address is set to `localhost`. You can specify the host address using the `--host <host>` argument. For example, to start the server on port 8081 and local address such that it is accessible from other machines on the network, you can run the following command:

```bash
autogenstudio ui --port 8081 --host 0.0.0.0
```

## Q: How do I use AutoGen Studio with a different database?

A: By default, AutoGen Studio uses SQLite as the database. However, it uses the SQLModel library, which supports multiple database backends. You can use any database supported by SQLModel, such as PostgreSQL or MySQL. To use a different database, you need to specify the connection string for the database using the `--database-uri` argument when running the application. Example connection strings include:

- SQLite: `sqlite:///database.sqlite`
- PostgreSQL: `postgresql+psycopg://user:password@localhost/dbname`
- MySQL: `mysql+pymysql://user:password@localhost/dbname`
- AzureSQL: `mssql+pyodbc:///?odbc_connect=DRIVER%3D%7BODBC+Driver+17+for+SQL+Server%7D%3BSERVER%3Dtcp%3Aservername.database.windows.net%2C1433%3BDATABASE%3Ddatabasename%3BUID%3Dusername%3BPWD%3Dpassword123%3BEncrypt%3Dyes%3BTrustServerCertificate%3Dno%3BConnection+Timeout%3D30%3B`

You can then run the application with the specified database URI. For example, to use PostgreSQL, you can run the following command:

```bash
autogenstudio ui --database-uri postgresql+psycopg://user:password@localhost/dbname
```

> **Note:** Make sure to install the appropriate database drivers for your chosen database:
>
> - PostgreSQL: `pip install psycopg2` or `pip install psycopg2-binary`
> - MySQL: `pip install pymysql`
> - SQL Server/Azure SQL: `pip install pyodbc`
> - Oracle: `pip install cx_oracle`

## Q: Can I export my agent workflows for use in a python app?

Yes. In the Team Builder view, you select a team and download its specification. This file can be imported in a python application using the `TeamManager` class. For example:

```python

from autogenstudio.teammanager import TeamManager

tm = TeamManager()
result_stream =  tm.run(task="What is the weather in New York?", team_config="team.json") # or wm.run_stream(..)

```

You can also load the team specification as an AgentChat object using the `load_component` method.

```python

import json
from autogen_agentchat.teams import BaseGroupChat
team_config = json.load(open("team.json"))
team = BaseGroupChat.load_component(team_config)

```

## Q: Can I run AutoGen Studio in a Docker container?

A: Yes, you can run AutoGen Studio in a Docker container. You can build the Docker image using the provided [Dockerfile](https://github.com/microsoft/autogen/blob/autogenstudio/samples/apps/autogen-studio/Dockerfile) and run the container using the following commands:

```bash
FROM python:3.10-slim

WORKDIR /code

RUN pip install -U gunicorn autogenstudio

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    AUTOGENSTUDIO_APPDIR=/home/user/app

WORKDIR $HOME/app

COPY --chown=user . $HOME/app

CMD gunicorn -w $((2 * $(getconf _NPROCESSORS_ONLN) + 1)) --timeout 12600 -k uvicorn.workers.UvicornWorker autogenstudio.web.app:app --bind "0.0.0.0:8081"
```

Using Gunicorn as the application server for improved performance is recommended. To run AutoGen Studio with Gunicorn, you can use the following command:

```bash
gunicorn -w $((2 * $(getconf _NPROCESSORS_ONLN) + 1)) --timeout 12600 -k uvicorn.workers.UvicornWorker autogenstudio.web.app:app --bind
```
