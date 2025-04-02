import copy
from dataclasses import dataclass
from typing import List

import pytest
from autogen_core import (
    AgentId,
    DefaultTopicId,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    default_subscription,
    message_handler,
)
from autogen_core.models import ChatCompletionClient, CreateResult, SystemMessage, UserMessage
from autogen_ext.models.replay import ReplayChatCompletionClient


@dataclass
class ContentMessage:
    content: str


class LLMAgent(RoutedAgent):
    def __init__(self, model_client: ChatCompletionClient) -> None:
        super().__init__("LLM Agent!")
        self._chat_history: List[ContentMessage] = []
        self._model_client = model_client
        self.num_calls = 0

    @message_handler
    async def on_new_message(self, message: ContentMessage, ctx: MessageContext) -> None:
        self._chat_history.append(message)
        self.num_calls += 1
        completion = await self._model_client.create(messages=self._fixed_message_history_type)
        if isinstance(completion.content, str):
            await self.publish_message(ContentMessage(content=completion.content), DefaultTopicId())
        else:
            raise TypeError(f"Completion content of type {type(completion.content)} is not supported")

    @property
    def _fixed_message_history_type(self) -> List[SystemMessage]:
        return [SystemMessage(content=msg.content) for msg in self._chat_history]


@default_subscription
class LLMAgentWithDefaultSubscription(LLMAgent): ...


@pytest.mark.asyncio
async def test_replay_chat_completion_client() -> None:
    num_messages = 5
    messages = [f"Message {i}" for i in range(num_messages)]
    reply_model_client = ReplayChatCompletionClient(messages)

    for i in range(num_messages):
        completion: CreateResult = await reply_model_client.create([UserMessage(content="dummy", source="_")])
        assert completion.content == messages[i]
    with pytest.raises(ValueError, match="No more mock responses available"):
        await reply_model_client.create([UserMessage(content="dummy", source="_")])


@pytest.mark.asyncio
async def test_replay_chat_completion_client_create_stream() -> None:
    num_messages = 5
    messages = [f"Message {i}" for i in range(num_messages)]
    reply_model_client = ReplayChatCompletionClient(messages)

    for i in range(num_messages):
        chunks: List[str] = []
        result: CreateResult | None = None
        async for completion in reply_model_client.create_stream([UserMessage(content="dummy", source="_")]):
            if isinstance(completion, CreateResult):
                result = completion
            else:
                assert isinstance(completion, str)
                chunks.append(completion)
        assert result is not None
        assert "".join(chunks) == messages[i] == result.content

    with pytest.raises(ValueError, match="No more mock responses available"):
        await reply_model_client.create([UserMessage(content="dummy", source="_")])


@pytest.mark.asyncio
async def test_register_receives_publish_llm() -> None:
    runtime = SingleThreadedAgentRuntime()
    runtime.start()

    reply_model_client_1 = ReplayChatCompletionClient(["Hi!", "Doing Good, you?", "Bye!"])
    reply_model_client_2 = ReplayChatCompletionClient(["Hi! How are you doing?", "Good, nice to meet you, bye!"])

    # First registered models gets the first message
    assert reply_model_client_1.provided_message_count == 1 + reply_model_client_2.provided_message_count

    await LLMAgentWithDefaultSubscription.register(
        runtime, "LLMAgent1", lambda: LLMAgentWithDefaultSubscription(reply_model_client_1)
    )

    await LLMAgentWithDefaultSubscription.register(
        runtime, "LLMAgent2", lambda: LLMAgentWithDefaultSubscription(reply_model_client_2)
    )

    await runtime.publish_message(ContentMessage(content="Let's get started!"), DefaultTopicId())
    await runtime.stop_when_idle()

    agent_1 = await runtime.try_get_underlying_agent_instance(
        AgentId("LLMAgent1", key="default"), type=LLMAgentWithDefaultSubscription
    )

    agent_2 = await runtime.try_get_underlying_agent_instance(
        AgentId("LLMAgent2", key="default"), type=LLMAgentWithDefaultSubscription
    )

    assert agent_1.num_calls == 1 + reply_model_client_2.provided_message_count
    assert agent_2.num_calls == 1 + reply_model_client_1.provided_message_count


@pytest.mark.asyncio
async def test_token_count_logics() -> None:
    phrases = [
        "This is a test message.",
        "This is another test message.",
        "This is yet another test message.",
        "Maybe even more messages?",
    ]
    reply_model_client = ReplayChatCompletionClient(phrases)

    messages = [UserMessage(content="How many tokens are in this message?", source="_")]

    token_count = reply_model_client.count_tokens(messages)
    assert token_count == 7

    _ = await reply_model_client.create(messages)
    remaining_tokens = reply_model_client.remaining_tokens(messages)
    assert remaining_tokens == 9988

    multiple_messages = [UserMessage(content="This is another test message.", source="_")]
    total_token_count = reply_model_client.count_tokens(messages + multiple_messages)
    assert total_token_count == 12

    before_cteate_usage = copy.deepcopy(reply_model_client.total_usage())
    completion: CreateResult = await reply_model_client.create(messages)

    assert completion.usage.prompt_tokens == 7
    assert completion.usage.completion_tokens == 5

    after_create_usage = reply_model_client.total_usage()
    assert after_create_usage.prompt_tokens > before_cteate_usage.prompt_tokens
    assert after_create_usage.completion_tokens > before_cteate_usage.completion_tokens

    before_cteate_stream_usage = copy.deepcopy(reply_model_client.total_usage())

    async for _ in reply_model_client.create_stream(messages):
        pass
    after_create_stream_usage = reply_model_client.total_usage()
    assert after_create_stream_usage.completion_tokens > before_cteate_stream_usage.completion_tokens
    assert after_create_stream_usage.prompt_tokens > before_cteate_stream_usage.prompt_tokens


@pytest.mark.asyncio
async def test_replay_chat_completion_client_reset() -> None:
    """Test that reset functionality properly resets the client state."""
    messages = ["First message", "Second message", "Third message"]
    client = ReplayChatCompletionClient(messages)

    # Use all messages once
    for expected_msg in messages:
        completion = await client.create([UserMessage(content="dummy", source="_")])
        assert completion.content == expected_msg

    # Should raise error when no more messages
    with pytest.raises(ValueError, match="No more mock responses available"):
        await client.create([UserMessage(content="dummy", source="_")])

    # Reset the client
    client.reset()

    # Should be able to get all messages again in the same order
    for expected_msg in messages:
        completion = await client.create([UserMessage(content="dummy", source="_")])
        assert completion.content == expected_msg
