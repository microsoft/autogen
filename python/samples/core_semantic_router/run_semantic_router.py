"""
This example showcases using a Semantic Router
to dynamically route user messages to the most appropraite agent
for a conversation.

The Semantic Router Agent is responsible for receiving messages from the user,
identifying the intent of the message, and then routing the message to the
agent, by referencing an "Agent Registry". Using the
pub-sub model, messages are broadcast to the most appropriate agent.

In this example, the Agent Registry is a simple dictionary which maps
string-matched intents to agent names. In a more complex example, the
intent classifier may be more robust, and the agent registry could use a
technology such as Azure AI Search to host definitions for many agents.

For this example, there are 2 agents available, an "hr" agent and a "finance" agent.
Any requests that can not be classified as "hr" or "finance" will result in the conversation
ending with a Termination message.

"""

import asyncio
import platform

from _agents import UserProxyAgent, WorkerAgent
from _semantic_router_agent import SemanticRouterAgent
from _semantic_router_components import (
    AgentRegistryBase,
    FinalResult,
    IntentClassifierBase,
    UserProxyMessage,
    WorkerAgentMessage,
)
from autogen_core import ClosureAgent, ClosureContext, DefaultSubscription, DefaultTopicId, MessageContext
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntime


class MockIntentClassifier(IntentClassifierBase):
    def __init__(self):
        self.intents = {
            "finance_intent": ["finance", "money", "budget"],
            "hr_intent": ["hr", "human resources", "employee"],
        }

    async def classify_intent(self, message: str) -> str:
        for intent, keywords in self.intents.items():
            for keyword in keywords:
                if keyword in message:
                    return intent
        return "general"


class MockAgentRegistry(AgentRegistryBase):
    def __init__(self):
        self.agents = {"finance_intent": "finance", "hr_intent": "hr"}

    async def get_agent(self, intent: str) -> str:
        return self.agents[intent]


async def output_result(
    closure_ctx: ClosureContext, message: WorkerAgentMessage | FinalResult, ctx: MessageContext
) -> None:
    if isinstance(message, WorkerAgentMessage):
        print(f"{message.source} Agent: {message.content}")
        new_message = input("User response: ")
        await closure_ctx.publish_message(
            UserProxyMessage(content=new_message, source="user"),
            topic_id=DefaultTopicId(type=message.source, source="user"),
        )
    else:
        print(f"{message.source} Agent: {message.content}")
        print("Conversation ended")
        new_message = input("Enter a new conversation start: ")
        await closure_ctx.publish_message(
            UserProxyMessage(content=new_message, source="user"), topic_id=DefaultTopicId(type="default", source="user")
        )


async def run_workers():
    agent_runtime = GrpcWorkerAgentRuntime(host_address="localhost:50051")

    await agent_runtime.start()

    # Create the agents
    await WorkerAgent.register(agent_runtime, "finance", lambda: WorkerAgent("finance_agent"))
    await agent_runtime.add_subscription(DefaultSubscription(topic_type="finance", agent_type="finance"))

    await WorkerAgent.register(agent_runtime, "hr", lambda: WorkerAgent("hr_agent"))
    await agent_runtime.add_subscription(DefaultSubscription(topic_type="hr", agent_type="hr"))

    # Create the User Proxy Agent
    await UserProxyAgent.register(agent_runtime, "user_proxy", lambda: UserProxyAgent("user_proxy"))
    await agent_runtime.add_subscription(DefaultSubscription(topic_type="user_proxy", agent_type="user_proxy"))

    # A closure agent surfaces the final result to external systems (e.g. an API) so that the system can interact with the user
    await ClosureAgent.register_closure(
        agent_runtime,
        "closure_agent",
        output_result,
        subscriptions=lambda: [DefaultSubscription(topic_type="response", agent_type="closure_agent")],
    )

    # Create the Semantic Router
    agent_registry = MockAgentRegistry()
    intent_classifier = MockIntentClassifier()
    await SemanticRouterAgent.register(
        agent_runtime,
        "router",
        lambda: SemanticRouterAgent(name="router", agent_registry=agent_registry, intent_classifier=intent_classifier),
    )

    print("Agents registered, starting conversation")
    # Start the conversation
    message = input("Enter a message: ")
    await agent_runtime.publish_message(
        UserProxyMessage(content=message, source="user"), topic_id=DefaultTopicId(type="default", source="user")
    )

    if platform.system() == "Windows":
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await agent_runtime.stop()
    else:
        await agent_runtime.stop_when_signal()


if __name__ == "__main__":
    asyncio.run(run_workers())
