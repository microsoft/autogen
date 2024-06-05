
import pytest
from agnext.components.tools import BaseTool
from agnext.core import CancellationToken
from pydantic import BaseModel, Field


class MyArgs(BaseModel):
    query: str = Field(description="The description.")


class MyResult(BaseModel):
    result: str = Field(description="The other description.")


class MyTool(BaseTool[MyArgs, MyResult]):
    def __init__(self) -> None:
        super().__init__(
            args_type=MyArgs,
            return_type=MyResult,
            name="TestTool",
            description="Description of test tool.",
        )
        self.called_count = 0

    async def run(self, args: MyArgs, cancellation_token: CancellationToken) -> MyResult:
        self.called_count += 1
        return MyResult(result="value")

def test_tool_schema_generation() -> None:
    schema = MyTool().schema

    assert schema["name"] == "TestTool"
    assert schema["description"] == "Description of test tool."
    assert schema["parameters"]["query"]["description"] == "The description."
    assert len(schema["parameters"]) == 1

@pytest.mark.asyncio
async def test_tool_run()-> None:
    tool = MyTool()
    result = await tool.run_json({"query": "test"}, CancellationToken())

    assert isinstance(result, MyResult)
    assert result.result == "value"
    assert tool.called_count == 1

    result = await tool.run_json({"query": "test"}, CancellationToken())
    result = await tool.run_json({"query": "test"}, CancellationToken())

    assert tool.called_count == 3


def test_tool_properties()-> None:
    tool = MyTool()

    assert tool.name == "TestTool"
    assert tool.description == "Description of test tool."
    assert tool.args_type() == MyArgs
    assert tool.return_type() == MyResult
    assert tool.state_type() is None
