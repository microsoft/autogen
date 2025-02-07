# AgentChat App with FastAPI

This sample demonstrates how to create a simple chat application using
[AgentChat](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/index.html)
and [FastAPI](https://fastapi.tiangolo.com/).

You will be using the following features of AgentChat:

1. Agent:
   - `AssistantAgent`
   - `UserProxyAgent` with a custom websocket input function
2. Team: `RoundRobinGroupChat`
3. State persistence: `save_state` and `load_state` methods of both agent and team.

## Setup

Install the required packages with OpenAI support:

```bash
pip install -U "autogen-ext[openai]" "fastapi" "uvicorn" "PyYAML"
```

To use models other than OpenAI, see the [Models](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/models.html) documentation.

Create a new file named `model_config.yaml` in the same directory as this README file to configure your model settings.
See `model_config_template.yaml` for an example.

## Chat with a single agent

To start the FastAPI server for single-agent chat, run:

```bash
python app_agent.py
```

Visit http://localhost:8001 in your browser to start chatting.

## Chat with a team of agents

To start the FastAPI server for team chat, run:

```bash
python app_team.py
```

Visit http://localhost:8002 in your browser to start chatting.

The team also includes a `UserProxyAgent` agent with a custom websocket input function
that allows the user to send messages to the team from the browser.

The team follows a round-robin strategy so each agent will take turns to respond.
When it is the user's turn, the input box will be enabled.
Once the user sends a message, the input box will be disabled and the agents
will take turns to respond.

## State persistence

The agents and team use the `load_state` and `save_state` methods to load and save
their state from and to files on each turn.
For the agent, the state is saved to and loaded from `agent_state.json`.
For the team, the state is saved to and loaded from `team_state.json`.
You can inspect the state files to see the state of the agents and team
once you have chatted with them.

When the server restarts, the agents and team will load their state from the state files
to maintain their state across restarts.

Additionally, the apps uses separate JSON files,
`agent_history.json` and `team_history.json`, to store the conversation history
for display in the browser.
