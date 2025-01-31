# AgentChat Chess Game

This is a simple chess game that you can play with an AI agent.

## Setup

Install the `chess` package with the following command:

```bash
pip install "chess"
```

To use OpenAI models or models hosted on OpenAI-compatible API endpoints,
you need to install the `autogen-ext[openai]` package. You can install it with the following command:

```bash
pip install "autogen-ext[openai]"
# pip install "autogen-ext[openai,azure]" for Azure OpenAI models
```

Create a new file named `model_config.yaml` in the the same directory as the script
to configure the model you want to use.

For example, to use `gpt-4o` model from OpenAI, you can use the following configuration:

```yaml
provider: autogen_ext.models.openai.OpenAIChatCompletionClient
config:
  model: gpt-4o
  api_key: REPLACE_WITH_YOUR_API_KEY
```

To use a locally hosted DeepSeek-R1:8b model using Ollama throught its compatibility endpoint,
you can use the following configuration:

```yaml
provider: autogen_ext.models.openai.OpenAIChatCompletionClient
config:
  model: deepseek-r1:8b
  base_url: http://localhost:11434/v1
  api_key: ollama
  model_info:
    function_calling: false
    json_output: false
    vision: false
    family: r1
```

For more information on how to configure the model and use other providers,
please refer to the [Models documentation](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/models.html).

## Run

Run the following command to start the game:

```bash
python chess_game.py
```

By default, the game will use a random agent to play against the AI agent.
You can enable human vs AI mode by setting the `--human` flag:

```bash
python chess_game.py --human
```
