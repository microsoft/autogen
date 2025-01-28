# Building a Multi-Agent Application with AutoGen and Chainlit

In this sample, we will build a simple chat interface that interacts with a `RoundRobinGroupChat` team built using the [AutoGen AgentChat](https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/index.html) api.

![AgentChat](docs/chainlit_autogen.png).

## High-Level Description

The `app.py` script sets up a Chainlit chat interface that communicates with the AutoGen team. When a chat starts, it

- Initializes an AgentChat team.

```python

async def get_weather(city: str) -> str:
    return f"The weather in {city} is 73 degrees and Sunny."

assistant_agent = AssistantAgent(
    name="assistant_agent",
    tools=[get_weather],
    model_client=OpenAIChatCompletionClient(
        model="gpt-4o-2024-08-06"))


termination = TextMentionTermination("TERMINATE") | MaxMessageTermination(10)
team = RoundRobinGroupChat(
    participants=[assistant_agent], termination_condition=termination)

```

- As users interact with the chat, their queries are sent to the team which responds.
- As agents respond/act, their responses are streamed back to the chat interface.

## Quickstart

To get started, ensure you have setup an API Key. We will be using the OpenAI API for this example.

1. Ensure you have an OPENAPI API key. Set this key in your environment variables as `OPENAI_API_KEY`.

2. Install the required Python packages by running:

```shell
pip install -r requirements.txt
```

3. Run the `app.py` script to start the Chainlit server.

```shell
chainlit run app.py -h
```

4. Interact with the Agent Team Chainlit interface. The chat interface will be available at `http://localhost:8000` by default.

### Function Definitions

- `start_chat`: Initializes the chat session
- `run_team`: Sends the user's query to the team streams the agent responses back to the chat interface.
- `chat`: Receives messages from the user and passes them to the `run_team` function.


## Adding a UserProxyAgent

We can add a `UserProxyAgent` to the team so that the user can interact with the team directly with the input box in the chat interface. This requires defining a function for input that uses the Chainlit input box instead of the terminal.

```python
from typing import Optional
from autogen_core import CancellationToken
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def chainlit_input_func(prompt: str, cancellation_token: Optional[CancellationToken] = None) -> str:
    try:
        response = await cl.AskUserMessage(
            content=prompt,
            author="System",
        ).send()
        return response["output"]

    except Exception as e:
        raise RuntimeError(f"Failed to get user input: {str(e)}") from e

user_proxy_agent = UserProxyAgent(
    name="user_proxy_agent",
    input_func=chainlit_input_func,
)
assistant_agent = AssistantAgent(
    name="assistant_agent",
    model_client=OpenAIChatCompletionClient(
        model="gpt-4o-2024-08-06"))

termination = TextMentionTermination("TERMINATE") | MaxMessageTermination(10)

team = RoundRobinGroupChat(
    participants=[user_proxy_agent, assistant_agent],
    termination_condition=termination)
```



## Next Steps (Extra Credit)

In this example, we created a basic AutoGen team with a single agent in a RoundRobinGroupChat team. There are a few ways you can extend this example:

- Add more [agents](https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/tutorial/agents.html) to the team.
- Explore custom agents that sent multimodal messages
- Explore more [team](https://microsoft.github.io/autogen/dev/user-guide/agentchat-user-guide/tutorial/teams.html) types beyond the `RoundRobinGroupChat`.
