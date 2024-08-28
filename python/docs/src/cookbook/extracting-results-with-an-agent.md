# Extracting Results with an Agent

When running a multi-agent system to solve some task, you may want to extract the result of the system once it has reached termination. This guide showcases one way to achieve this. Given that agent instances are not directly accessible from the outside, we will use an agent to publish the final result to an accessible location.

If you model your system to publish some `FinalResult` type then you can create an agent whose sole job is to subscribe to this and make it available externally. For simple agents like this the {py:class}`~autogen_core.components.ClosureAgent` is an option to reduce the amount of boilerplate code. This allows you to define a function that will be associated as the agent's message handler. In this example, we're going to use a queue shared between the agent and the external code to pass the result.

```{note}
When considering how to extract results from a multi-agent system, you must always consider the namespace of the agent and by extension the message.
```

```python
from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import AgentRuntime, AgentId, CancellationToken
from autogen_core.components import ClosureAgent

import asyncio

@dataclass
class FinalResult:
    result: str

# ...

queue = asyncio.Queue[tuple[str, FinalResult]]()

async def output_result(_runtime: AgentRuntime, id: AgentId, message: FinalResult, cancellation_token: CancellationToken) -> None:
    namespace = id.namespace
    await queue.put((namespace, FinalResult))

runtime.register("OutputResult", lambda: ClosureAgent("Outputs messages", output_result))

# ...
```

When using a `ClosureAgent` the third parameter, named `message` in this example determines what messages are subscribed to. In this case, the agent will only receive messages of type `FinalResult`. This can also be a union of types if you want to subscribe to multiple types of messages.
