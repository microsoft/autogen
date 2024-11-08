import pytest
from autogen_core.components.models import CreateResult, UserMessage
from test_utils.client_test_utils import ReplayChatCompletionClient


@pytest.mark.asyncio
async def test_reply_chat_completion_client() -> None:
    num_messages = 5
    messages = [f"Message {i}" for i in range(num_messages)]
    reply_model_client = ReplayChatCompletionClient(messages)

    for i in range(num_messages):
        completion: CreateResult = await reply_model_client.create([UserMessage(content="dummy", source="_")])
        assert completion.content == messages[i]
    with pytest.raises(ValueError):
        await reply_model_client.create([UserMessage(content="dummy", source="_")])


@pytest.mark.asyncio
async def test_reply_chat_completion_client_create_stream() -> None:
    num_messages = 5
    messages = [f"Message {i}" for i in range(num_messages)]
    reply_model_client = ReplayChatCompletionClient(messages)

    for i in range(num_messages):
        result = []
        async for completion in reply_model_client.create_stream([UserMessage(content="dummy", source="_")]):
            text = completion.content if isinstance(completion, CreateResult) else completion
            result.append(text)
        assert "".join(result) == messages[i]

    with pytest.raises(ValueError):
        await reply_model_client.create([UserMessage(content="dummy", source="_")])
