import logging
from typing import Optional, Type, cast

import pytest
from autogen_core import CancellationToken
from autogen_core.tools import Tool
from autogen_ext.tools.langchain import LangChainToolAdapter  # type: ignore
from langchain_core.callbacks.manager import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
from langchain_core.tools import BaseTool as LangChainTool
from langchain_core.tools import tool  # pyright: ignore
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


class ToolWithoutSchema(LangChainTool):
    """A tool without args_schema that has callback parameters (for testing fix)."""
    name: str = "NoSchemaTool"
    description: str = "A tool without args_schema for testing callback filtering"
    return_direct: bool = True

    def _run(self, query: str, limit: int = 10, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Search with optional callback."""
        return f"Searched for: {query} (limit: {limit})"

    async def _arun(
        self,
        query: str,
        limit: int = 10,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        """Async version."""
        return self._run(query, limit, run_manager=run_manager.get_sync() if run_manager else None)


@pytest.mark.asyncio
async def test_langchain_tool_adapter(caplog: pytest.LogCaptureFixture) -> None:
    # Create a LangChain tool
    langchain_tool = add  # type: ignore

    # Create an adapter
    adapter = cast(Tool, LangChainToolAdapter(langchain_tool))  # type: ignore

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

    # Check log.
    with caplog.at_level(logging.INFO):
        # Test run method
        result = await adapter.run_json({"a": 2, "b": 3}, CancellationToken())
        assert result == 5
        assert str(result) in caplog.text

    # Test that the adapter's run method can be called multiple times
    result = await adapter.run_json({"a": 5, "b": 7}, CancellationToken())
    assert result == 12

    # Test CustomCalculatorTool
    custom_langchain_tool = CustomCalculatorTool()
    custom_adapter = LangChainToolAdapter(custom_langchain_tool)  # type: ignore

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

    # Test ToolWithoutSchema (tool without args_schema, with callback parameters)
    # This tests the fix for issue #6385
    no_schema_tool = ToolWithoutSchema()
    no_schema_adapter = LangChainToolAdapter(no_schema_tool)  # type: ignore

    # Test schema generation - should filter out run_manager callback
    no_schema_schema = no_schema_adapter.schema
    assert no_schema_schema["name"] == "NoSchemaTool"
    assert "parameters" in no_schema_schema
    assert "properties" in no_schema_schema["parameters"]
    # Should have query and limit, but NOT run_manager
    assert "query" in no_schema_schema["parameters"]["properties"]
    assert "limit" in no_schema_schema["parameters"]["properties"]
    assert "run_manager" not in no_schema_schema["parameters"]["properties"]

    # Test run method
    no_schema_result = await no_schema_adapter.run_json({"query": "test", "limit": 5}, CancellationToken())
    assert no_schema_result == "Searched for: test (limit: 5)"
