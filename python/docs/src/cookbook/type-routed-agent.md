# Using Type Routed Agent

To make it easier to implement agents that respond to certain message types there is a base class called {py:class}`~agnext.components.RoutedAgent`. This class provides a simple decorator pattern for associating message types with message handlers.

The decorator {py:func}`agnext.components.message_handler` should be added to functions in the class that are intended to handle messages. These functions have a specific signature that needs to be followed for it to be recognized as a message handler.

- The function must be an `async` function.
- The function must be decorated with the `message_handler` decorator.
- The function must have exactly 3 arguments.
  - `self`
  - `message`: The message to be handled, this must be type hinted with the message type that it is intended to handle.
  - `cancellation_token`: A {py:class}`agnext.core.CancellationToken` object
- The function must be type hinted with what message types it can return.

```{tip}
Handlers can handle more than one message type by accepting a Union of the message types. It can also return more than one message type by returning a Union of the message types.
```

## Example

The following is an example of a simple agent that broadcasts the fact it received messages, and resets its internal counter when it receives a reset message.

One important thing to point out is that when an agent is constructed it must be passed a runtime object. This allows the agent to communicate with other agents via the runtime.

```python
from dataclasses import dataclass
from typing import List, Union
from agnext.components import RoutedAgent, message_handler, Image
from agnext.core import AgentRuntime, CancellationToken

@dataclass
class TextMessage:
    content: str
    source: str

@dataclass
class MultiModalMessage:
    content: List[Union[str, Image]]
    source: str

@dataclass
class Reset:
    pass


class MyAgent(RoutedAgent):
    def __init__(self):
        super().__init__(description="I am a demo agent")
        self._received_count = 0

    @message_handler()
    async def on_text_message(
        self, message: TextMessage | MultiModalMessage, cancellation_token: CancellationToken
    ) -> None:
        self._received_count += 1
        await self.publish_message(
            TextMessage(
                content=f"I received a message from {message.source}. Message received #{self._received_count}",
                source=self.metadata["type"],
            )
        )

    @message_handler()
    async def on_reset(self, message: Reset, cancellation_token: CancellationToken) -> None:
        self._received_count = 0
```
