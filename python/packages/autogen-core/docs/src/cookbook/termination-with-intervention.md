# Termination using Intervention Handler

```{note}
This method is only really valid for single-tenant applications. If multiple parallel users are using the application via namespaces this approach will not work without modification.
```

There are many different ways to handle termination in `autogen_core`. Ultimately, the goal is to detect that the runtime no longer needs to be executed and you can proceed to finalization tasks. One way to do this is to use an `InterventionHandler` to detect a termination message and then act on it.

```python
import asyncio
from dataclasses import dataclass
from typing import Any

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.components import RoutedAgent, message_handler
from autogen_core.base import AgentId, CancellationToken
from autogen_core.base.intervention import DefaultInterventionHandler
```

First, we define a dataclass that will be used to signal termination.

```python
@dataclass
class Termination:
    reason: str
```

We code our agent to publish a termination message when it decides it is time to terminate.

```python
class AnAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("MyAgent")
        self.received = 0

    @message_handler
    async def on_new_message(self, message: str, cancellation_token: CancellationToken) -> None:
        self.received += 1
        if self.received > 3:
            self.publish_message(Termination(reason="Reached maximum number of messages"))
```

Next, we create an InterventionHandler that will detect the termination message and act on it. This one hooks into publishes and when it encounters `Termination` it alters its internal state to indicate that termination has been requested.
```python

class TerminationHandler(DefaultInterventionHandler):

    def __init__(self):
        self.termination_value: Termination | None = None

    async def on_publish(self, message: Any, *, sender: AgentId | None) -> Any:
        if isinstance(message, Termination):
            self.termination_value = message
        return message

    @property
    def termination_value(self) -> Termination | None:
        return self.termination_value

    @property
    def has_terminated(self) -> bool:
        return self.termination_value is not None
```

Finally, we add this handler to the runtime and use it to detect termination and cease running the `process_next` loop once it has encountered termination.

```python
async def main() -> None:
    termination_handler = TerminationHandler()
    runtime = SingleThreadedAgentRuntime(
        intervention_handler=termination_handler
    )

    # Add Agents and kick off task

    while not termination_handler.has_terminated:
        await runtime.process_next()

    print(termination_handler.termination_value)


if __name__ == "__main__":
    asyncio.run(main())
```
