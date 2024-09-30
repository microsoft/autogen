from typing import Optional, Type

import pytest
from autogen_core.base import CancellationToken
from autogen_ext.tools.langchain import LangChainToolAdapter  # type: ignore
from langchain.tools import BaseTool as LangChainTool  # type: ignore
from langchain.tools import tool  # pyright: ignore
from langchain_core.callbacks.manager import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
from pydantic import BaseModel, Field


@tool  # type: ignore
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


class CalculatorInput(BaseModel):
    a: int = Field(description="first number")
    b: int = Field(description="second number")


class CustomCalculatorTool(LangChainTool):
    name: str = "Calculator"
    description: str = "useful for when you need to answer questions about math"
    args_schema: Type[BaseModel] = CalculatorInput
    return_direct: bool = True

    def _run(self, a: int, b: int, run_manager: Optional[CallbackManagerForToolRun] = None) -> int:
        """Use the tool."""
        return a * b

    async def _arun(
        self,
        a: int,
        b: int,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> int:
        """Use the tool asynchronously."""
        return self._run(a, b, run_manager=run_manager.get_sync() if run_manager else None)


@pytest.mark.asyncio
async def test_langchain_tool_adapter() -> None:
    # Create a LangChain tool
    langchain_tool = add  # type: ignore

    # Create an adapter
    adapter = LangChainToolAdapter(langchain_tool)  # pyright: ignore

    # Test schema generation
    schema = adapter.schema

    assert schema["name"] == "add"
    assert "description" in schema
    assert schema["description"] == "Add two numbers"
    assert "parameters" in schema
    assert schema["parameters"]["type"] == "object"
    assert "properties" in schema["parameters"]
    assert "a" in schema["parameters"]["properties"]
    assert "b" in schema["parameters"]["properties"]
    assert schema["parameters"]["properties"]["a"]["type"] == "integer"
    assert schema["parameters"]["properties"]["b"]["type"] == "integer"
    assert "required" in schema["parameters"]
    assert set(schema["parameters"]["required"]) == {"a", "b"}
    assert len(schema["parameters"]["properties"]) == 2

    # Test run method
    result = await adapter.run_json({"a": 2, "b": 3}, CancellationToken())
    assert result == 5

    # Test that the adapter's run method can be called multiple times
    result = await adapter.run_json({"a": 5, "b": 7}, CancellationToken())
    assert result == 12

    # Test CustomCalculatorTool
    custom_langchain_tool = CustomCalculatorTool()
    custom_adapter = LangChainToolAdapter(custom_langchain_tool)  # pyright: ignore

    # Test schema generation for CustomCalculatorTool
    custom_schema = custom_adapter.schema

    assert custom_schema["name"] == "Calculator"
    assert custom_schema["description"] == "useful for when you need to answer questions about math"  # type: ignore
    assert "parameters" in custom_schema
    assert custom_schema["parameters"]["type"] == "object"
    assert "properties" in custom_schema["parameters"]
    assert "a" in custom_schema["parameters"]["properties"]
    assert "b" in custom_schema["parameters"]["properties"]
    assert custom_schema["parameters"]["properties"]["a"]["type"] == "integer"
    assert custom_schema["parameters"]["properties"]["b"]["type"] == "integer"
    assert "required" in custom_schema["parameters"]
    assert set(custom_schema["parameters"]["required"]) == {"a", "b"}

    # Test run method for CustomCalculatorTool
    custom_result = await custom_adapter.run_json({"a": 3, "b": 4}, CancellationToken())
    assert custom_result == 12
