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
chainlit run app.py
```

4. Interact with the Agent Team Chainlit interface.

### Function Definitions

- `start_chat`: Initializes the chat session and sets up the avatar for Claude.
- `run_team`: Sends the user's query to the Anthropic API and streams the response back to the chat interface.
- `chat`: Receives messages from the user and passes them to the `call_claude` function.

## Next Steps (Extra Credit)

In this example, we created a basic AutoGen team with a single agent, Claude. There are a few ways you can extend this example:

- Add more agents to the team.
- Explor custom agents that sent multimodal messages
- Explore more team types beyond the `RoundRobinGroupChat`.
