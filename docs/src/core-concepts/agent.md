# Agent

An agent in AGNext is an entity that can react to, send, and publish
messages. Messages are the only means through which agents can communicate
with each others.

## TypeRoutedAgent

{py:class}`agnext.components.TypeRoutedAgent`
is a base class for building custom agents. It provides
a simple API for associating message types with message handlers.
Here is an example of simple agent that reacts to `TextMessage`:

```python
from agnext.chat.types import TextMessage
from agnext.components import TypeRoutedAgent, message_handler
from agnext.core import AgentRuntime, CancellationToken

class MyAgent(TypeRoutedAgent):

    @message_handler()
    async def on_text_message(self, message: TextMessage, cancellation_token: CancellationToken)) -> None:
        await self._publish(TextMessage(content=f"I received this message: ({message.content}) from {message.source}"))
```
