import pytest
from autogen_core import CancellationToken
from autogen_ext.runtimes.a2a._a2a_external_user_proxy_agent import (
    A2aExternalUserProxyAgent,
    A2aExternalUserProxyAgentConfig,
)


@pytest.fixture
def agent() -> A2aExternalUserProxyAgent:
    return A2aExternalUserProxyAgent()


@pytest.mark.asyncio
async def test_initialization(agent: A2aExternalUserProxyAgent) -> None:
    """Test basic initialization of A2aExternalUserProxyAgent."""
    assert agent.name == "ExternalUser"
    assert agent.is_cancelled_by_me is False
    assert "proxy user agent" in agent.description.lower()


@pytest.mark.asyncio
async def test_cancel_for_user_input(agent: A2aExternalUserProxyAgent) -> None:
    """Test cancel_for_user_input behavior."""
    token = CancellationToken()
    result = await agent.cancel_for_user_input("Test prompt", token)

    assert agent.is_cancelled_by_me is True
    assert token.is_cancelled() is True
    assert "cancelled" in result.lower()


@pytest.mark.asyncio
async def test_cancel_for_user_input_no_token() -> None:
    """Test cancel_for_user_input with no token raises error."""
    agent = A2aExternalUserProxyAgent()
    with pytest.raises(AssertionError, match="Cancellation token must be provided"):
        await agent.cancel_for_user_input("Test prompt", None)


@pytest.mark.asyncio
async def test_reset(agent: A2aExternalUserProxyAgent) -> None:
    """Test reset functionality."""
    # First cancel to set is_cancelled_by_me to True
    token = CancellationToken()
    await agent.cancel_for_user_input("Test prompt", token)
    assert agent.is_cancelled_by_me is True

    # Then reset
    await agent.on_reset()
    assert agent.is_cancelled_by_me is False


@pytest.mark.asyncio
async def test_save_and_load_state(agent: A2aExternalUserProxyAgent) -> None:
    """Test state saving and loading."""
    # Set up initial state
    token = CancellationToken()
    await agent.cancel_for_user_input("Test prompt", token)
    assert agent.is_cancelled_by_me is True

    # Save state
    state = await agent.save_state()
    assert isinstance(state, dict)
    assert state["is_cancelled_by_me"] is True

    # Create new agent and load state
    new_agent = A2aExternalUserProxyAgent()
    await new_agent.load_state(state)
    assert new_agent.is_cancelled_by_me is True


@pytest.mark.asyncio
async def test_from_config() -> None:
    """Test _from_config class method."""
    config = A2aExternalUserProxyAgentConfig()
    agent = A2aExternalUserProxyAgent._from_config(config)
    assert isinstance(agent, A2aExternalUserProxyAgent)
    assert agent.is_cancelled_by_me is False
