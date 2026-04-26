"""
core_group_chat_example.py

Demonstrates a group chat multi-agent workflow in AutoGen Core API:
- WriterAgent: Writes story content
- IllustratorAgent: Generates illustrations (DALL-E, optional)
- EditorAgent: Reviews and guides
- UserAgent: Human user for approval
- GroupChatManager: Selects next speaker (LLM-based)

Agents share a common topic and take turns, coordinated by the manager.

To run:
    python core_group_chat_example.py

Note: Requires OPENAI_API_KEY in environment for OpenAI examples. DALL-E image generation is optional and requires additional setup.
"""
import asyncio
import json
import string
import uuid
from typing import List

try:
    from autogen_core import (
        DefaultTopicId, FunctionCall, Image, MessageContext, RoutedAgent, SingleThreadedAgentRuntime, TopicId, TypeSubscription, message_handler
    )
    from autogen_core.models import AssistantMessage, ChatCompletionClient, LLMMessage, SystemMessage, UserMessage
    from autogen_core.tools import FunctionTool
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    from pydantic import BaseModel
    from rich.console import Console
    from rich.markdown import Markdown
except ImportError as e:
    print("Required packages not installed:", e)
    print("Please install autogen-core, autogen-ext, and rich.")
    exit(1)

# Message protocol
class GroupChatMessage(BaseModel):
    body: UserMessage

class RequestToSpeak(BaseModel):
    pass

# Base group chat agent
class BaseGroupChatAgent(RoutedAgent):
    def __init__(self, description: str, group_chat_topic_type: str, model_client: ChatCompletionClient, system_message: str) -> None:
        super().__init__(description=description)
        self._group_chat_topic_type = group_chat_topic_type
        self._model_client = model_client
        self._system_message = SystemMessage(content=system_message)
        self._chat_history: List[LLMMessage] = []

    @message_handler
    async def handle_message(self, message: GroupChatMessage, ctx: MessageContext) -> None:
        self._chat_history.extend([
            UserMessage(content=f"Transferred to {message.body.source}", source="system"),
            message.body,
        ])

    @message_handler
    async def handle_request_to_speak(self, message: RequestToSpeak, ctx: MessageContext) -> None:
        Console().print(Markdown(f"### {self.id.type}: "))
        self._chat_history.append(UserMessage(content=f"Transferred to {self.id.type}, adopt the persona immediately.", source="system"))
        completion = await self._model_client.create([self._system_message] + self._chat_history)
        assert isinstance(completion.content, str)
        self._chat_history.append(AssistantMessage(content=completion.content, source=self.id.type))
        Console().print(Markdown(completion.content))
        await self.publish_message(
            GroupChatMessage(body=UserMessage(content=completion.content, source=self.id.type)),
            topic_id=DefaultTopicId(type=self._group_chat_topic_type),
        )

# Writer and Editor agents
class WriterAgent(BaseGroupChatAgent):
    def __init__(self, description: str, group_chat_topic_type: str, model_client: ChatCompletionClient) -> None:
        super().__init__(
            description=description,
            group_chat_topic_type=group_chat_topic_type,
            model_client=model_client,
            system_message="You are a Writer. You produce good work.",
        )

class EditorAgent(BaseGroupChatAgent):
    def __init__(self, description: str, group_chat_topic_type: str, model_client: ChatCompletionClient) -> None:
        super().__init__(
            description=description,
            group_chat_topic_type=group_chat_topic_type,
            model_client=model_client,
            system_message="You are an Editor. Plan and guide the task given by the user. Provide critical feedbacks to the draft and illustration produced by Writer and Illustrator. Approve if the task is completed and the draft and illustration meets user's requirements.",
        )

# Illustrator agent (image generation is optional)
class IllustratorAgent(BaseGroupChatAgent):
    def __init__(self, description: str, group_chat_topic_type: str, model_client: ChatCompletionClient):
        super().__init__(
            description=description,
            group_chat_topic_type=group_chat_topic_type,
            model_client=model_client,
            system_message="You are an Illustrator. You describe the image you would generate for the story. (DALL-E integration optional)",
        )

    # For demonstration, just describe the image instead of generating it
    @message_handler
    async def handle_request_to_speak(self, message: RequestToSpeak, ctx: MessageContext) -> None:
        Console().print(Markdown(f"### {self.id.type}: "))
        self._chat_history.append(UserMessage(content=f"Transferred to {self.id.type}, adopt the persona immediately.", source="system"))
        completion = await self._model_client.create([self._system_message] + self._chat_history)
        assert isinstance(completion.content, str)
        self._chat_history.append(AssistantMessage(content=completion.content, source=self.id.type))
        Console().print(Markdown(completion.content))
        await self.publish_message(
            GroupChatMessage(body=UserMessage(content=completion.content, source=self.id.type)),
            DefaultTopicId(type=self._group_chat_topic_type),
        )

# User agent
class UserAgent(RoutedAgent):
    def __init__(self, description: str, group_chat_topic_type: str) -> None:
        super().__init__(description=description)
        self._group_chat_topic_type = group_chat_topic_type

    @message_handler
    async def handle_message(self, message: GroupChatMessage, ctx: MessageContext) -> None:
        pass  # In a real app, send to frontend

    @message_handler
    async def handle_request_to_speak(self, message: RequestToSpeak, ctx: MessageContext) -> None:
        user_input = input("Enter your message, type 'APPROVE' to conclude the task: ")
        Console().print(Markdown(f"### User: \n{user_input}"))
        await self.publish_message(
            GroupChatMessage(body=UserMessage(content=user_input, source=self.id.type)),
            DefaultTopicId(type=self._group_chat_topic_type),
        )

# Group chat manager
class GroupChatManager(RoutedAgent):
    def __init__(self, participant_topic_types: List[str], model_client: ChatCompletionClient, participant_descriptions: List[str]) -> None:
        super().__init__("Group chat manager")
        self._participant_topic_types = participant_topic_types
        self._model_client = model_client
        self._chat_history: List[UserMessage] = []
        self._participant_descriptions = participant_descriptions
        self._previous_participant_topic_type: str | None = None

    @message_handler
    async def handle_message(self, message: GroupChatMessage, ctx: MessageContext) -> None:
        assert isinstance(message.body, UserMessage)
        self._chat_history.append(message.body)
        if message.body.source == "User":
            if isinstance(message.body.content, str) and message.body.content.lower().strip(string.punctuation).endswith("approve"):
                return
        messages: List[str] = []
        for msg in self._chat_history:
            if isinstance(msg.content, str):
                messages.append(f"{msg.source}: {msg.content}")
            elif isinstance(msg.content, list):
                line: List[str] = []
                for item in msg.content:
                    if isinstance(item, str):
                        line.append(item)
                    else:
                        line.append("[Image]")
                messages.append(f"{msg.source}: {', '.join(line)}")
        history = "\n".join(messages)
        roles = "\n".join(
            [
                f"{topic_type}: {description}".strip()
                for topic_type, description in zip(self._participant_topic_types, self._participant_descriptions, strict=True)
                if topic_type != self._previous_participant_topic_type
            ]
        )
        selector_prompt = """You are in a role play game. The following roles are available:
{roles}.
Read the following conversation. Then select the next role from {participants} to play. Only return the role.

{history}

Read the above conversation. Then select the next role from {participants} to play. Only return the role.
"""
        system_message = SystemMessage(
            content=selector_prompt.format(
                roles=roles,
                history=history,
                participants=str([
                    topic_type
                    for topic_type in self._participant_topic_types
                    if topic_type != self._previous_participant_topic_type
                ]),
            )
        )
        completion = await self._model_client.create([system_message], cancellation_token=ctx.cancellation_token)
        assert isinstance(completion.content, str)
        for topic_type in self._participant_topic_types:
            if topic_type.lower() in completion.content.lower():
                selected_topic_type = topic_type
                self._previous_participant_topic_type = selected_topic_type
                await self.publish_message(RequestToSpeak(), DefaultTopicId(type=selected_topic_type))
                return
        raise ValueError(f"Invalid role selected: {completion.content}")

async def main():
    runtime = SingleThreadedAgentRuntime()
    editor_topic_type = "Editor"
    writer_topic_type = "Writer"
    illustrator_topic_type = "Illustrator"
    user_topic_type = "User"
    group_chat_topic_type = "group_chat"
    editor_description = "Editor for planning and reviewing the content."
    writer_description = "Writer for creating any text content."
    user_description = "User for providing final approval."
    illustrator_description = "An illustrator for creating images."
    model_client = OpenAIChatCompletionClient(model="gpt-4o-2024-08-06")
    editor_agent_type = await EditorAgent.register(
        runtime,
        editor_topic_type,
        lambda: EditorAgent(description=editor_description, group_chat_topic_type=group_chat_topic_type, model_client=model_client),
    )
    await runtime.add_subscription(TypeSubscription(topic_type=editor_topic_type, agent_type=editor_agent_type.type))
    await runtime.add_subscription(TypeSubscription(topic_type=group_chat_topic_type, agent_type=editor_agent_type.type))
    writer_agent_type = await WriterAgent.register(
        runtime,
        writer_topic_type,
        lambda: WriterAgent(description=writer_description, group_chat_topic_type=group_chat_topic_type, model_client=model_client),
    )
    await runtime.add_subscription(TypeSubscription(topic_type=writer_topic_type, agent_type=writer_agent_type.type))
    await runtime.add_subscription(TypeSubscription(topic_type=group_chat_topic_type, agent_type=writer_agent_type.type))
    illustrator_agent_type = await IllustratorAgent.register(
        runtime,
        illustrator_topic_type,
        lambda: IllustratorAgent(description=illustrator_description, group_chat_topic_type=group_chat_topic_type, model_client=model_client),
    )
    await runtime.add_subscription(TypeSubscription(topic_type=illustrator_topic_type, agent_type=illustrator_agent_type.type))
    await runtime.add_subscription(TypeSubscription(topic_type=group_chat_topic_type, agent_type=illustrator_agent_type.type))
    user_agent_type = await UserAgent.register(
        runtime,
        user_topic_type,
        lambda: UserAgent(description=user_description, group_chat_topic_type=group_chat_topic_type),
    )
    await runtime.add_subscription(TypeSubscription(topic_type=user_topic_type, agent_type=user_agent_type.type))
    await runtime.add_subscription(TypeSubscription(topic_type=group_chat_topic_type, agent_type=user_agent_type.type))
    group_chat_manager_type = await GroupChatManager.register(
        runtime,
        "group_chat_manager",
        lambda: GroupChatManager(
            participant_topic_types=[writer_topic_type, illustrator_topic_type, editor_topic_type, user_topic_type],
            model_client=model_client,
            participant_descriptions=[writer_description, illustrator_description, editor_description, user_description],
        ),
    )
    await runtime.add_subscription(TypeSubscription(topic_type=group_chat_topic_type, agent_type=group_chat_manager_type.type))
    runtime.start()
    session_id = str(uuid.uuid4())
    await runtime.publish_message(
        GroupChatMessage(
            body=UserMessage(
                content="Please write a short story about the gingerbread man with up to 3 photo-realistic illustrations.",
                source="User",
            )
        ),
        TopicId(type=group_chat_topic_type, source=session_id),
    )
    await runtime.stop_when_idle()
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
