# CancellationToken Propagation

`CancellationToken` is the mechanism AutoGen uses to request cooperative cancellation of long-running operations. When you call `cancel()` on a token, any code that is watching that token should stop promptly and clean up.

## Propagation contract

The token must be forwarded through every layer that can block:

1. **Team / group chat** — `run()` and `run_stream()` accept a `cancellation_token` and pass it to every agent message handler they invoke.
2. **Agent message handler** — `on_messages()` and `on_messages_stream()` receive the token and must forward it to any tool or workbench they call.
3. **Workbench / tool call** — `call_tool()` and `call_tool_stream()` receive the token and must pass it into the underlying tool execution.
4. **Tool implementation** — `run_json()` and `run_stream()` receive the token and should check `is_cancelled()` between blocking operations, or pass it into async operations that support cancellation (e.g. `asyncio.sleep`, HTTP requests).

If any layer drops the token, cancellation stops at that boundary and the operation continues running in the background.

## Example: cancellable nested tool

```python
import asyncio
from autogen_core import CancellationToken, FunctionCall
from autogen_core.tools import Tool, ToolSchema
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient


class SlowTool(Tool):
    def __init__(self) -> None:
        super().__init__(name="slow", description="Sleeps for 10 seconds")

    @property
    def schema(self) -> ToolSchema:
        return {"type": "function", "name": self.name, "description": self.description, "parameters": {}}

    async def run_json(self, arguments: str, cancellation_token: CancellationToken, call_id: str) -> str:
        # The token is forwarded by the workbench; we can observe it here.
        for _ in range(10):
            if cancellation_token.is_cancelled():
                return "cancelled"
            await asyncio.sleep(1)
        return "done"


async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4o")
    agent = AssistantAgent(
        name="assistant",
        model_client=model_client,
        tools=[SlowTool()],
        system_message="Use the slow tool when asked.",
    )
    token = CancellationToken()
    task = asyncio.create_task(agent.run(task="Use the slow tool", cancellation_token=token))
    await asyncio.sleep(2)
    token.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("Task was cancelled")


asyncio.run(main())
```

## Boundaries that must forward the token

When you write custom agents, workbenches, or tools, these are the call sites that must accept and forward `CancellationToken`:

- `BaseChatAgent.on_messages(..., cancellation_token)`
- `BaseChatAgent.on_messages_stream(..., cancellation_token)`
- `Workbench.call_tool(..., cancellation_token)`
- `Workbench.call_tool_stream(..., cancellation_token)`
- `Tool.run_json(..., cancellation_token, call_id)`
- `Tool.run_stream(..., cancellation_token, call_id)`

## Observing cancellation in a tool

A tool should check `cancellation_token.is_cancelled()` at safe points during long-running work. For async loops, check between iterations. For blocking calls, run them in a thread and check the token before and after.

```python
async def run_json(self, arguments: str, cancellation_token: CancellationToken, call_id: str) -> str:
    if cancellation_token.is_cancelled():
        return "cancelled before start"
    result = await asyncio.get_event_loop().run_in_executor(None, blocking_work)
    if cancellation_token.is_cancelled():
        return "cancelled after blocking work"
    return result
```
