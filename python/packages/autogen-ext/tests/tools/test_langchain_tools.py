import logging
from typing import Optional, Type, cast

import pytest
from autogen_core import CancellationToken
from autogen_core.tools import Tool
from autogen_ext.tools.langchain import LangChainToolAdapter  # type: ignore
from langchain_core.callbacks import Callbacks
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


class NoSchemaTool(LangChainTool):
    name: str = "NoSchema"
    description: str = "a tool without an explicit args schema"

    def _run(self, a: int, b: int, run_manager: Optional[CallbackManagerForToolRun] = None) -> int:
        return a + b

    async def _arun(
        self,
        a: int,
        b: int,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> int:
        return a + b


@pytest.mark.asyncio
async def test_langchain_tool_adapter_skips_run_manager() -> None:
    # Tools without an explicit args_schema get their args inferred from the
    # callable's signature. LangChain injects a ``run_manager`` into ``_run``
    # which is not a user-facing input and cannot be turned into a pydantic
    # schema; the adapter must skip it (see #6385).
    tool = NoSchemaTool()
    adapter = LangChainToolAdapter(tool)  # type: ignore

    schema = adapter.schema
    assert schema["name"] == "NoSchema"
    assert "parameters" in schema
    assert "properties" in schema["parameters"]
    props = schema["parameters"]["properties"]
    assert "run_manager" not in props
    assert set(props.keys()) == {"a", "b"}
    assert "required" in schema["parameters"]
    assert set(schema["parameters"]["required"]) == {"a", "b"}

    result = await adapter.run_json({"a": 2, "b": 3}, CancellationToken())
    assert result == 5


class NoSchemaCallbacksTool(LangChainTool):
    name: str = "NoSchemaCallbacks"
    description: str = "a tool without an explicit args schema that also accepts callbacks"

    def _run(self, a: int, b: int, callbacks: Callbacks = None) -> int:
        return a + b

    async def _arun(self, a: int, b: int, callbacks: Callbacks = None) -> int:
        return a + b


@pytest.mark.asyncio
async def test_langchain_tool_adapter_skips_callbacks() -> None:
    # In addition to ``run_manager``, LangChain also reserves ``callbacks`` (a
    # ``Callbacks`` sequence of handlers) as a runtime-only argument -- it is in
    # LangChain's ``FILTERED_ARGS``. Its annotation is not matched by
    # ``_is_callback_manager_annotation``, so the adapter must skip it by name;
    # otherwise inferring the args schema raises PydanticSchemaGenerationError.
    tool = NoSchemaCallbacksTool()
    adapter = LangChainToolAdapter(tool)  # type: ignore

    schema = adapter.schema
    assert schema["name"] == "NoSchemaCallbacks"
    assert "parameters" in schema
    assert "properties" in schema["parameters"]
    props = schema["parameters"]["properties"]
    assert "callbacks" not in props
    assert set(props.keys()) == {"a", "b"}
    assert "required" in schema["parameters"]
    assert set(schema["parameters"]["required"]) == {"a", "b"}

    result = await adapter.run_json({"a": 2, "b": 3}, CancellationToken())
    assert result == 5


class NoSchemaAsyncManagerTool(LangChainTool):
    name: str = "NoSchemaAsyncManager"
    description: str = "a tool whose sync _run is annotated with the async callback manager type"

    def _run(self, a: int, b: int, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> int:
        return a + b

    async def _arun(self, a: int, b: int, run_manager: Optional[AsyncCallbackManagerForToolRun] = None) -> int:
        return a + b


@pytest.mark.asyncio
async def test_langchain_tool_adapter_skips_async_run_manager() -> None:
    # The detection must cover the *async* callback-manager type
    # (``AsyncCallbackManagerForToolRun``), not only the sync
    # ``CallbackManagerForToolRun``. ``_is_callback_manager_annotation`` unwraps
    # ``Optional[...]`` and matches both via ``issubclass``, so a tool that
    # annotates its signature with the async variant is still filtered out.
    tool = NoSchemaAsyncManagerTool()
    adapter = LangChainToolAdapter(tool)  # type: ignore

    schema = adapter.schema
    assert schema["name"] == "NoSchemaAsyncManager"
    assert "parameters" in schema
    assert "properties" in schema["parameters"]
    props = schema["parameters"]["properties"]
    assert "run_manager" not in props
    assert set(props.keys()) == {"a", "b"}
    assert "required" in schema["parameters"]
    assert set(schema["parameters"]["required"]) == {"a", "b"}

    result = await adapter.run_json({"a": 2, "b": 3}, CancellationToken())
    assert result == 5
