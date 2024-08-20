import asyncio
import json

import pytest
from agnext.application import SingleThreadedAgentRuntime
from agnext.components import FunctionCall
from agnext.components.models import FunctionExecutionResult
from agnext.components.tool_agent import (
    InvalidToolArgumentsException,
    ToolAgent,
    ToolExecutionException,
    ToolNotFoundException,
)
from agnext.components.tools import FunctionTool
from agnext.core import CancellationToken
from agnext.core import AgentId


def _pass_function(input: str) -> str:
    return "pass"


def _raise_function(input: str) -> str:
    raise Exception("raise")


async def _async_sleep_function(input: str) -> str:
    await asyncio.sleep(10)
    return "pass"


@pytest.mark.asyncio
async def test_tool_agent() -> None:
    runtime = SingleThreadedAgentRuntime()
    await runtime.register(
        "tool_agent",
        lambda: ToolAgent(
            description="Tool agent",
            tools=[
                FunctionTool(_pass_function, name="pass", description="Pass function"),
                FunctionTool(_raise_function, name="raise", description="Raise function"),
                FunctionTool(_async_sleep_function, name="sleep", description="Sleep function"),
            ],
        ),
    )
    agent = AgentId("tool_agent", "default")
    run = runtime.start()

    # Test pass function
    result = await runtime.send_message(
        FunctionCall(id="1", arguments=json.dumps({"input": "pass"}), name="pass"), agent
    )
    assert result == FunctionExecutionResult(call_id="1", content="pass")

    # Test raise function
    with pytest.raises(ToolExecutionException):
        await runtime.send_message(FunctionCall(id="2", arguments=json.dumps({"input": "raise"}), name="raise"), agent)

    # Test invalid tool name
    with pytest.raises(ToolNotFoundException):
        await runtime.send_message(FunctionCall(id="3", arguments=json.dumps({"input": "pass"}), name="invalid"), agent)

    # Test invalid arguments
    with pytest.raises(InvalidToolArgumentsException):
        await runtime.send_message(FunctionCall(id="3", arguments="invalid json /xd", name="pass"), agent)

    # Test sleep and cancel.
    token = CancellationToken()
    result_future = runtime.send_message(
        FunctionCall(id="3", arguments=json.dumps({"input": "sleep"}), name="sleep"), agent, cancellation_token=token
    )
    token.cancel()
    with pytest.raises(asyncio.CancelledError):
        await result_future

    await run.stop()
