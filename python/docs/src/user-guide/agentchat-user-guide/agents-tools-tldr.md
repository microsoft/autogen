# Agents and Tools TL;DR

## Creating a Custom Agent

Subclass `BaseChatAgent` and implement three members: `on_messages`, `on_reset`, and the
`produced_message_types` property. Optionally implement `on_messages_stream` for streaming.

```python
from typing import AsyncGenerator, Sequence
from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import BaseAgentEvent, BaseChatMessage, TextMessage
from autogen_core import CancellationToken

class MyAgent(BaseChatAgent):
    def __init__(self, name: str):
        super().__init__(name, "My custom agent description.")

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (TextMessage,)

    async def on_messages(
        self, messages: Sequence[BaseChatMessage], cancellation_token: CancellationToken
    ) -> Response:
        # Implement your logic here
        reply = TextMessage(content="Hello from MyAgent!", source=self.name)
        return Response(chat_message=reply)

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        pass  # Reset internal state here
```

Custom agents are drop-in compatible with all AgentChat teams (`RoundRobinGroupChat`,
`SelectorGroupChat`, etc.) as long as they inherit from `BaseChatAgent`.

## Adding Tools to an Agent

Any Python async function becomes a tool automatically when passed to `AssistantAgent`.
Use type annotations and a docstring — they are sent to the model as the tool schema.

```python
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return f"The weather in {city} is 72 degrees and sunny."

async def web_search(query: str) -> str:
    """Search the web for information."""
    return "AutoGen is a multi-agent framework by Microsoft."

agent = AssistantAgent(
    name="assistant",
    model_client=OpenAIChatCompletionClient(model="gpt-4o"),
    tools=[get_weather, web_search],      # plain functions work directly
    system_message="Use tools to answer questions.",
    reflect_on_tool_use=True,             # model summarizes tool output
)
```

For the Core API, wrap functions with `FunctionTool` from `autogen_core.tools`:

```python
from autogen_core.tools import FunctionTool
tool = FunctionTool(get_weather, description="Get weather for a city.")
```

## Tool Types Available

| Type | Where | Description |
|------|-------|-------------|
| Python function | AgentChat / Core | Auto-converted; schema from annotations + docstring |
| `FunctionTool` | Core | Explicit wrapper with custom description |
| `PythonCodeExecutionTool` | `autogen_ext` | Runs Python code in a sandboxed executor |
| `HttpTool` | `autogen_ext` | Makes HTTP requests to REST APIs |
| `McpWorkbench` | `autogen_ext` | Connects to MCP servers (stateful tool sessions) |
| `LangChainToolAdapter` | `autogen_ext` | Wraps LangChain tools |
| `AgentTool` | AgentChat | Wraps an agent so another agent can call it as a tool |

## Human-in-the-Loop Basics

To require human approval at runtime, include a `UserProxyAgent` in a team, or use
`HandoffTermination` to pause and let the application inject a human message:

```python
from autogen_agentchat.agents import UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import TextMentionTermination

user_proxy = UserProxyAgent(name="human")
agent = AssistantAgent(name="assistant", model_client=model_client)
team = RoundRobinGroupChat(
    [agent, user_proxy],
    termination_condition=TextMentionTermination("TERMINATE"),
)
```

The `UserProxyAgent` will prompt for console input when it is its turn to respond.

## Further Reading

- Agent tutorial (tool use, structured output, streaming): `tutorial/agents.ipynb`
- Custom agents in depth: `custom-agents.ipynb`
- Core tools reference: `core-user-guide/components/tools.ipynb`
- Human-in-the-loop tutorial: `tutorial/human-in-the-loop.ipynb`
