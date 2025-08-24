"""Tests for custom tool implementations."""

import pytest
from autogen_core import CancellationToken
from autogen_core.tools._custom_tool import (
    CodeExecutorTool,
    CodeResult,
    SQLQueryTool,
    SQLResult,
    TimestampResult,
    TimestampTool,
)


@pytest.mark.asyncio
async def test_code_executor_tool_short_input() -> None:
    """Test CodeExecutorTool with short input text."""
    tool = CodeExecutorTool()
    result = await tool.run("print('hello')", CancellationToken())

    assert isinstance(result, CodeResult)
    assert result.output == "Executed code: print('hello')"


@pytest.mark.asyncio
async def test_code_executor_tool_long_input() -> None:
    """Test CodeExecutorTool with input longer than 100 characters."""
    tool = CodeExecutorTool()
    long_code = "x = " + "1" * 100  # 104 characters total
    result = await tool.run(long_code, CancellationToken())

    assert isinstance(result, CodeResult)
    assert result.output == f"Executed code: {long_code[:100]}..."
    assert "..." in result.output


def test_code_executor_tool_properties() -> None:
    """Test CodeExecutorTool properties."""
    tool = CodeExecutorTool()

    assert tool.name == "code_exec"
    assert tool.description == "Executes arbitrary Python code"
    assert tool.return_type() == CodeResult

    schema = tool.schema
    assert schema["name"] == "code_exec"
    assert schema.get("description") == "Executes arbitrary Python code"
    assert "format" not in schema


@pytest.mark.asyncio
async def test_sql_query_tool_execution() -> None:
    """Test SQLQueryTool query execution."""
    tool = SQLQueryTool()
    query = "SELECT id FROM users WHERE age > 18;"
    result = await tool.run(query, CancellationToken())

    assert isinstance(result, SQLResult)
    assert result.output == f"SQL Result: Executed query '{query}'"


def test_sql_query_tool_properties() -> None:
    """Test SQLQueryTool properties and grammar format."""
    tool = SQLQueryTool()

    assert tool.name == "sql_query"
    assert tool.description == "Executes SQL queries with grammar constraints"
    assert tool.return_type() == SQLResult

    schema = tool.schema
    assert schema["name"] == "sql_query"
    assert schema.get("description") == "Executes SQL queries with grammar constraints"
    assert "format" in schema

    format_spec = schema.get("format")
    assert format_spec is not None
    assert format_spec.get("type") == "grammar"
    assert format_spec.get("syntax") == "lark"
    assert "start: select_statement" in format_spec.get("definition", "")


@pytest.mark.asyncio
async def test_timestamp_tool_execution() -> None:
    """Test TimestampTool timestamp saving."""
    tool = TimestampTool()
    timestamp = "2024-01-15 14:30"
    result = await tool.run(timestamp, CancellationToken())

    assert isinstance(result, TimestampResult)
    assert result.message == f"Saved timestamp: {timestamp}"


def test_timestamp_tool_properties() -> None:
    """Test TimestampTool properties and regex format."""
    tool = TimestampTool()

    assert tool.name == "save_timestamp"
    assert tool.description == "Saves a timestamp in YYYY-MM-DD HH:MM format"
    assert tool.return_type() == TimestampResult

    schema = tool.schema
    assert schema["name"] == "save_timestamp"
    assert schema.get("description") == "Saves a timestamp in YYYY-MM-DD HH:MM format"
    assert "format" in schema

    format_spec = schema.get("format")
    assert format_spec is not None
    assert format_spec.get("type") == "grammar"
    assert format_spec.get("syntax") == "regex"
    assert r"^\d{4}" in format_spec.get("definition", "")  # Should contain year pattern


def test_all_tools_inheritance() -> None:
    """Test that all custom tools properly inherit from BaseCustomTool."""
    from autogen_core.tools._base import BaseCustomTool

    code_tool = CodeExecutorTool()
    sql_tool = SQLQueryTool()
    timestamp_tool = TimestampTool()

    assert isinstance(code_tool, BaseCustomTool)
    assert isinstance(sql_tool, BaseCustomTool)
    assert isinstance(timestamp_tool, BaseCustomTool)


def test_result_models() -> None:
    """Test that result models can be instantiated correctly."""
    code_result = CodeResult(output="test output")
    sql_result = SQLResult(output="test sql output")
    timestamp_result = TimestampResult(message="test message")

    assert code_result.output == "test output"
    assert sql_result.output == "test sql output"
    assert timestamp_result.message == "test message"
