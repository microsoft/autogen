"""
core_agent_and_runtime_example.py

Demonstrates the foundational concepts of AutoGen Core API: agents, agent runtime, messages, direct messaging, broadcast, type-based routing, and subscriptions.

This example covers:
- Defining message types (dataclasses)
- Implementing agents by subclassing RoutedAgent
- Registering agent types with the runtime
- Direct messaging (request/response)
- Broadcast (publish/subscribe) with type-based subscription
- Using match parameter for handler routing
- Default topic/subscription convenience

To run:
    python core_agent_and_runtime_example.py
"""
import asyncio
from dataclasses import dataclass
from autogen_core import (
    AgentId, MessageContext, RoutedAgent, SingleThreadedAgentRuntime, message_handler,
    type_subscription, TopicId, TypeSubscription, DefaultTopicId, default_subscription
)

# --- Message Types ---
@dataclass
class TextMessage:
    content: str
    source: str

@dataclass
class ImageMessage:
    url: str
    source: str

@dataclass
class SimpleMessage:
    content: str

# --- Agents ---
class MyAgent(RoutedAgent):
    def __init__(self, name: str = "MyAgent"):
        super().__init__(name)

    @message_handler
    async def on_text_message(self, message: TextMessage, ctx: MessageContext) -> None:
        print(f"[MyAgent] Hello, {message.source}, you said: {message.content}")

    @message_handler
    async def on_image_message(self, message: ImageMessage, ctx: MessageContext) -> None:
        print(f"[MyAgent] Hello, {message.source}, you sent: {message.url}")

# --- Routing by sender ---
class RoutedBySenderAgent(RoutedAgent):
    def __init__(self, name: str = "RoutedBySenderAgent"):
        super().__init__(name)

    @message_handler(match=lambda msg, ctx: msg.source.startswith("user1"))
    async def on_user1_message(self, message: TextMessage, ctx: MessageContext) -> None:
        print(f"[RoutedBySenderAgent] user1 handler: {message.source} said {message.content}")

    @message_handler(match=lambda msg, ctx: msg.source.startswith("user2"))
    async def on_user2_message(self, message: TextMessage, ctx: MessageContext) -> None:
        print(f"[RoutedBySenderAgent] user2 handler: {message.source} said {message.content}")

    @message_handler(match=lambda msg, ctx: msg.source.startswith("user2"))
    async def on_image_message(self, message: ImageMessage, ctx: MessageContext) -> None:
        print(f"[RoutedBySenderAgent] user2 image: {message.source} sent {message.url}")

# --- Direct messaging (request/response) ---
class InnerAgent(RoutedAgent):
    def __init__(self, name: str = "InnerAgent"):
        super().__init__(name)

    @message_handler
    async def on_simple_message(self, message: SimpleMessage, ctx: MessageContext) -> SimpleMessage:
        return SimpleMessage(content=f"Hello from inner, {message.content}")

class OuterAgent(RoutedAgent):
    def __init__(self, name: str, inner_agent_type: str):
        super().__init__(name)
        self.inner_agent_id = AgentId(inner_agent_type, self.id.key)

    @message_handler
    async def on_simple_message(self, message: SimpleMessage, ctx: MessageContext) -> None:
        print(f"[OuterAgent] Received: {message.content}")
        response = await self.send_message(SimpleMessage(f"Hello from outer, {message.content}"), self.inner_agent_id)
        print(f"[OuterAgent] Inner response: {response.content}")

# --- Broadcast/Subscribe ---
@type_subscription(topic_type="default")
class ReceivingAgent(RoutedAgent):
    def __init__(self, name: str = "ReceivingAgent"):
        super().__init__(name)

    @message_handler
    async def on_simple_message(self, message: SimpleMessage, ctx: MessageContext) -> None:
        print(f"[ReceivingAgent] Received broadcast: {message.content}")

class BroadcastingAgent(RoutedAgent):
    def __init__(self, name: str = "BroadcastingAgent"):
        super().__init__(name)

    @message_handler
    async def on_simple_message(self, message: SimpleMessage, ctx: MessageContext) -> None:
        await self.publish_message(
            SimpleMessage("Publishing a message from broadcasting agent!"),
            topic_id=TopicId(type="default", source=self.id.key),
        )

# --- Default topic/subscription convenience ---
@default_subscription
class BroadcastingAgentDefaultTopic(RoutedAgent):
    def __init__(self, name: str = "BroadcastingAgentDefaultTopic"):
        super().__init__(name)

    @message_handler
    async def on_simple_message(self, message: SimpleMessage, ctx: MessageContext) -> None:
        await self.publish_message(
            SimpleMessage("Publishing a message from broadcasting agent (default topic)!"),
            topic_id=DefaultTopicId(),
        )

# --- Main demo ---
async def main():
    runtime = SingleThreadedAgentRuntime()

    # Register agents
    await MyAgent.register(runtime, "my_agent", lambda: MyAgent())
    await RoutedBySenderAgent.register(runtime, "routed_by_sender_agent", lambda: RoutedBySenderAgent())
    await InnerAgent.register(runtime, "inner_agent", lambda: InnerAgent())
    await OuterAgent.register(runtime, "outer_agent", lambda: OuterAgent("OuterAgent", "inner_agent"))
    await ReceivingAgent.register(runtime, "receiving_agent", lambda: ReceivingAgent())
    await BroadcastingAgent.register(runtime, "broadcasting_agent", lambda: BroadcastingAgent())
    await BroadcastingAgentDefaultTopic.register(runtime, "broadcasting_agent_default", lambda: BroadcastingAgentDefaultTopic())

    # Add type subscription for broadcasting agent
    await runtime.add_subscription(TypeSubscription(topic_type="default", agent_type="broadcasting_agent"))

    print("\n--- Direct messaging (type-based routing) ---")
    runtime.start()
    agent_id = AgentId("my_agent", "default")
    await runtime.send_message(TextMessage(content="Hello, World!", source="User"), agent_id)
    await runtime.send_message(ImageMessage(url="https://example.com/image.jpg", source="User"), agent_id)
    await runtime.stop_when_idle()

    print("\n--- Routing by sender ---")
    runtime.start()
    agent_id = AgentId("routed_by_sender_agent", "default")
    await runtime.send_message(TextMessage(content="Hello, World!", source="user1-test"), agent_id)
    await runtime.send_message(TextMessage(content="Hello, World!", source="user2-test"), agent_id)
    await runtime.send_message(ImageMessage(url="https://example.com/image.jpg", source="user1-test"), agent_id)
    await runtime.send_message(ImageMessage(url="https://example.com/image.jpg", source="user2-test"), agent_id)
    await runtime.stop_when_idle()

    print("\n--- Direct messaging (request/response) ---")
    runtime.start()
    outer_agent_id = AgentId("outer_agent", "default")
    await runtime.send_message(SimpleMessage(content="Hello, World!"), outer_agent_id)
    await runtime.stop_when_idle()

    print("\n--- Broadcast/Subscribe ---")
    runtime.start()
    await runtime.publish_message(SimpleMessage("Hello, World! From the runtime!"), topic_id=TopicId(type="default", source="default"))
    await runtime.stop_when_idle()

    print("\n--- Default topic/subscription convenience ---")
    runtime.start()
    await runtime.publish_message(SimpleMessage("Hello, World! From the runtime! (default topic)"), topic_id=DefaultTopicId())
    await runtime.stop_when_idle()

    await runtime.close()

if __name__ == "__main__":
    asyncio.run(main())
