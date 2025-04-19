import pytest
from autogen_agentchat.agents import (
    AssistantAgent,
    CodeExecutorAgent,
    SocietyOfMindAgent,
)
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core.model_context import (
    BufferedChatCompletionContext,
    ChatCompletionContext,
    HeadAndTailChatCompletionContext,
    TokenLimitedChatCompletionContext,
    UnboundedChatCompletionContext,
)
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.replay import ReplayChatCompletionClient


@pytest.mark.parametrize(
    "model_context_class",
    [
        UnboundedChatCompletionContext(),
        BufferedChatCompletionContext(buffer_size=5),
        TokenLimitedChatCompletionContext(model_client=ReplayChatCompletionClient([]), token_limit=5),
        HeadAndTailChatCompletionContext(head_size=3, tail_size=2),
    ],
)
def test_serialize_and_deserialize_model_context_on_assistant_agent(model_context_class: ChatCompletionContext) -> None:
    """Test the serialization and deserialization of the message context on the AssistantAgent."""
    agent = AssistantAgent(
        name="assistant",
        model_client=ReplayChatCompletionClient([]),
        description="An assistant agent.",
        model_context=model_context_class,
    )

    # Serialize the agent
    serialized_agent = agent.dump_component()
    # Deserialize the agent
    deserialized_agent = AssistantAgent.load_component(serialized_agent)

    # Check that the deserialized agent has the same model context as the original agent
    original_model_context = agent.model_context
    deserialized_model_context = deserialized_agent.model_context

    assert isinstance(original_model_context, type(deserialized_model_context))
    assert isinstance(deserialized_model_context, type(original_model_context))
    assert original_model_context.dump_component() == deserialized_model_context.dump_component()


@pytest.mark.parametrize(
    "model_context_class",
    [
        UnboundedChatCompletionContext(),
        BufferedChatCompletionContext(buffer_size=5),
        TokenLimitedChatCompletionContext(model_client=ReplayChatCompletionClient([]), token_limit=5),
        HeadAndTailChatCompletionContext(head_size=3, tail_size=2),
    ],
)
def test_serialize_and_deserialize_model_context_on_society_of_mind_agent(
    model_context_class: ChatCompletionContext,
) -> None:
    """Test the serialization and deserialization of the message context on the AssistantAgent."""
    agent1 = AssistantAgent(
        name="assistant1", model_client=ReplayChatCompletionClient([]), description="An assistant agent."
    )
    agent2 = AssistantAgent(
        name="assistant2", model_client=ReplayChatCompletionClient([]), description="An assistant agent."
    )
    team = RoundRobinGroupChat(
        participants=[agent1, agent2],
    )
    agent = SocietyOfMindAgent(
        name="assistant",
        model_client=ReplayChatCompletionClient([]),
        description="An assistant agent.",
        team=team,
        model_context=model_context_class,
    )

    # Serialize the agent
    serialized_agent = agent.dump_component()
    # Deserialize the agent
    deserialized_agent = SocietyOfMindAgent.load_component(serialized_agent)

    # Check that the deserialized agent has the same model context as the original agent
    original_model_context = agent.model_context
    deserialized_model_context = deserialized_agent.model_context

    assert isinstance(original_model_context, type(deserialized_model_context))
    assert isinstance(deserialized_model_context, type(original_model_context))
    assert original_model_context.dump_component() == deserialized_model_context.dump_component()


@pytest.mark.parametrize(
    "model_context_class",
    [
        UnboundedChatCompletionContext(),
        BufferedChatCompletionContext(buffer_size=5),
        TokenLimitedChatCompletionContext(model_client=ReplayChatCompletionClient([]), token_limit=5),
        HeadAndTailChatCompletionContext(head_size=3, tail_size=2),
    ],
)
def test_serialize_and_deserialize_model_context_on_code_executor_agent(
    model_context_class: ChatCompletionContext,
) -> None:
    """Test the serialization and deserialization of the message context on the AssistantAgent."""
    agent = CodeExecutorAgent(
        name="assistant",
        code_executor=LocalCommandLineCodeExecutor(),
        description="An assistant agent.",
        model_context=model_context_class,
    )

    # Serialize the agent
    serialized_agent = agent.dump_component()
    # Deserialize the agent
    deserialized_agent = CodeExecutorAgent.load_component(serialized_agent)

    # Check that the deserialized agent has the same model context as the original agent
    original_model_context = agent.model_context
    deserialized_model_context = deserialized_agent.model_context

    assert isinstance(original_model_context, type(deserialized_model_context))
    assert isinstance(deserialized_model_context, type(original_model_context))
    assert original_model_context.dump_component() == deserialized_model_context.dump_component()
