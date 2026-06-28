import inspect
import json
import logging
from dataclasses import dataclass
from functools import partial
from typing import Annotated, Any, List, Mapping

import pytest
from autogen_core import EVENT_LOGGER_NAME, CancellationToken
from autogen_core._function_utils import get_typed_signature
from autogen_core.tools import BaseStreamTool, BaseTool, FunctionTool
from autogen_core.tools._base import ToolSchema
from autogen_core.tools._guardrail import Decision, GuardrailDeniedError, GuardrailProvider, GuardrailResult
from pydantic import BaseModel, Field, ValidationError, model_serializer
from pydantic_core import PydanticUndefined


class MyArgs(BaseModel):
    query: str = Field(description="The description.")


class MyNestedArgs(BaseModel):
    arg: MyArgs = Field(description="The nested description.")


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


class MyNestedTool(BaseTool[MyNestedArgs, MyResult]):
    def __init__(self) -> None:
        super().__init__(
            args_type=MyNestedArgs,
            return_type=MyResult,
            name="TestNestedTool",
            description="Description of test nested tool.",
        )
        self.called_count = 0

    async def run(self, args: MyNestedArgs, cancellation_token: CancellationToken) -> MyResult:
        self.called_count += 1
        return MyResult(result="value")


class RecordingTool(BaseTool[MyArgs, MyResult]):
    def __init__(self) -> None:
        super().__init__(
            args_type=MyArgs,
            return_type=MyResult,
            name="RecordingTool",
            description="Records the effective args.",
        )
        self.last_args: MyArgs | None = None

    async def run(self, args: MyArgs, cancellation_token: CancellationToken) -> MyResult:
        self.last_args = args
        return MyResult(result=args.query)


class MyStreamTool(BaseStreamTool[MyArgs, MyResult, MyResult]):
    def __init__(self) -> None:
        super().__init__(MyArgs, MyResult, "TestStreamTool", "Description of test stream tool.")
        self.called_count = 0

    async def run(self, args: MyArgs, cancellation_token: CancellationToken) -> MyResult:
        self.called_count += 1
        return MyResult(result=args.query)

    async def run_stream(self, args: MyArgs, cancellation_token: CancellationToken):  # type: ignore[no-untyped-def]
        self.called_count += 1
        yield MyResult(result=args.query)


def test_tool_schema_generation() -> None:
    schema = MyTool().schema

    assert schema["name"] == "TestTool"
    assert "description" in schema
    assert schema["description"] == "Description of test tool."
    assert "parameters" in schema
    assert schema["parameters"]["type"] == "object"
    assert "properties" in schema["parameters"]
    assert schema["parameters"]["properties"]["query"]["description"] == "The description."
    assert schema["parameters"]["properties"]["query"]["type"] == "string"
    assert "required" in schema["parameters"]
    assert schema["parameters"]["required"] == ["query"]
    assert len(schema["parameters"]["properties"]) == 1


def test_func_tool_schema_generation() -> None:
    def my_function(arg: str, other: Annotated[int, "int arg"], nonrequired: int = 5) -> MyResult:
        return MyResult(result="test")

    tool = FunctionTool(my_function, description="Function tool.")
    schema = tool.schema

    assert schema["name"] == "my_function"
    assert "description" in schema
    assert schema["description"] == "Function tool."
    assert "parameters" in schema
    assert schema["parameters"]["type"] == "object"
    assert schema["parameters"]["properties"].keys() == {"arg", "other", "nonrequired"}
    assert schema["parameters"]["properties"]["arg"]["type"] == "string"
    assert schema["parameters"]["properties"]["arg"]["description"] == "arg"
    assert schema["parameters"]["properties"]["other"]["type"] == "integer"
    assert schema["parameters"]["properties"]["other"]["description"] == "int arg"
    assert schema["parameters"]["properties"]["nonrequired"]["type"] == "integer"
    assert schema["parameters"]["properties"]["nonrequired"]["description"] == "nonrequired"
    assert "required" in schema["parameters"]
    assert schema["parameters"]["required"] == ["arg", "other"]
    assert len(schema["parameters"]["properties"]) == 3


def test_func_tool_schema_generation_strict() -> None:
    def my_function1(arg: str, other: Annotated[int, "int arg"], nonrequired: int = 5) -> MyResult:
        return MyResult(result="test")

    with pytest.raises(ValueError, match="Strict mode is enabled"):
        tool = FunctionTool(my_function1, description="Function tool.", strict=True)
        schema = tool.schema

    def my_function2(arg: str, other: Annotated[int, "int arg"]) -> MyResult:
        return MyResult(result="test")

    tool = FunctionTool(my_function2, description="Function tool.", strict=True)
    schema = tool.schema

    assert schema["name"] == "my_function2"
    assert "description" in schema
    assert schema["description"] == "Function tool."
    assert "parameters" in schema
    assert schema["parameters"]["type"] == "object"
    assert schema["parameters"]["properties"].keys() == {"arg", "other"}
    assert schema["parameters"]["properties"]["arg"]["type"] == "string"
    assert schema["parameters"]["properties"]["arg"]["description"] == "arg"
    assert schema["parameters"]["properties"]["other"]["type"] == "integer"
    assert schema["parameters"]["properties"]["other"]["description"] == "int arg"
    assert "required" in schema["parameters"]
    assert schema["parameters"]["required"] == ["arg", "other"]
    assert len(schema["parameters"]["properties"]) == 2
    assert "additionalProperties" in schema["parameters"]
    assert schema["parameters"]["additionalProperties"] is False


def test_func_tool_schema_generation_only_default_arg() -> None:
    def my_function(arg: str = "default") -> MyResult:
        return MyResult(result="test")

    tool = FunctionTool(my_function, description="Function tool.")
    schema = tool.schema

    assert schema["name"] == "my_function"
    assert "description" in schema
    assert schema["description"] == "Function tool."
    assert "parameters" in schema
    assert len(schema["parameters"]["properties"]) == 1
    assert schema["parameters"]["properties"]["arg"]["type"] == "string"
    assert schema["parameters"]["properties"]["arg"]["description"] == "arg"
    assert "required" in schema["parameters"]
    assert schema["parameters"]["required"] == []


def test_func_tool_schema_generation_only_default_arg_strict() -> None:
    def my_function(arg: str = "default") -> MyResult:
        return MyResult(result="test")

    with pytest.raises(ValueError, match="Strict mode is enabled"):
        tool = FunctionTool(my_function, description="Function tool.", strict=True)
        _ = tool.schema


def test_func_tool_with_partial_positional_arguments_schema_generation() -> None:
    """Test correct schema generation for a partial function with positional arguments."""

    def get_weather(country: str, city: str) -> str:
        return f"The temperature in {city}, {country} is 75°"

    partial_function = partial(get_weather, "Germany")
    tool = FunctionTool(partial_function, description="Partial function tool.")
    schema = tool.schema

    assert schema["name"] == "get_weather"
    assert "description" in schema
    assert schema["description"] == "Partial function tool."
    assert "parameters" in schema
    assert schema["parameters"]["type"] == "object"
    assert schema["parameters"]["properties"].keys() == {"city"}
    assert schema["parameters"]["properties"]["city"]["type"] == "string"
    assert schema["parameters"]["properties"]["city"]["description"] == "city"
    assert "required" in schema["parameters"]
    assert schema["parameters"]["required"] == ["city"]
    assert "country" not in schema["parameters"]["properties"]  # check country not in schema params
    assert len(schema["parameters"]["properties"]) == 1


def test_func_call_tool_with_kwargs_schema_generation() -> None:
    """Test correct schema generation for a partial function with kwargs."""

    def get_weather(country: str, city: str) -> str:
        return f"The temperature in {city}, {country} is 75°"

    partial_function = partial(get_weather, country="Germany")
    tool = FunctionTool(partial_function, description="Partial function tool.")
    schema = tool.schema

    assert schema["name"] == "get_weather"
    assert "description" in schema
    assert schema["description"] == "Partial function tool."
    assert "parameters" in schema
    assert schema["parameters"]["type"] == "object"
    assert schema["parameters"]["properties"].keys() == {"country", "city"}
    assert schema["parameters"]["properties"]["city"]["type"] == "string"
    assert schema["parameters"]["properties"]["country"]["type"] == "string"
    assert "required" in schema["parameters"]
    assert schema["parameters"]["required"] == ["city"]  # only city is required
    assert len(schema["parameters"]["properties"]) == 2


@pytest.mark.asyncio
async def test_run_func_call_tool_with_kwargs_and_args() -> None:
    """Test run partial function with kwargs and args."""

    def get_weather(country: str, city: str, unit: str = "Celsius") -> str:
        return f"The temperature in {city}, {country} is 75° {unit}"

    partial_function = partial(get_weather, "Germany", unit="Fahrenheit")
    tool = FunctionTool(partial_function, description="Partial function tool.")
    result = await tool.run_json({"city": "Berlin"}, CancellationToken())
    assert isinstance(result, str)
    assert result == "The temperature in Berlin, Germany is 75° Fahrenheit"


@pytest.mark.asyncio
async def test_tool_run() -> None:
    tool = MyTool()
    result = await tool.run_json({"query": "test"}, CancellationToken())

    assert isinstance(result, MyResult)
    assert result.result == "value"
    assert tool.called_count == 1

    result = await tool.run_json({"query": "test"}, CancellationToken())
    result = await tool.run_json({"query": "test"}, CancellationToken())

    assert tool.called_count == 3


def test_tool_properties() -> None:
    tool = MyTool()

    assert tool.name == "TestTool"
    assert tool.description == "Description of test tool."
    assert tool.args_type() == MyArgs
    assert tool.return_type() == MyResult
    assert tool.state_type() is None


def test_get_typed_signature() -> None:
    def my_function() -> str:
        return "result"

    sig = get_typed_signature(my_function)
    assert isinstance(sig, inspect.Signature)
    assert len(sig.parameters) == 0
    assert sig.return_annotation is str


def test_get_typed_signature_annotated() -> None:
    def my_function() -> Annotated[str, "The return type"]:
        return "result"

    sig = get_typed_signature(my_function)
    assert isinstance(sig, inspect.Signature)
    assert len(sig.parameters) == 0
    assert sig.return_annotation == Annotated[str, "The return type"]


def test_get_typed_signature_string() -> None:
    def my_function() -> "str":
        return "result"

    sig = get_typed_signature(my_function)
    assert isinstance(sig, inspect.Signature)
    assert len(sig.parameters) == 0
    assert sig.return_annotation is str


def test_get_typed_signature_params() -> None:
    def my_function(arg: str) -> None:
        return None

    sig = get_typed_signature(my_function)
    assert isinstance(sig, inspect.Signature)
    assert sig.return_annotation is type(None)
    assert len(sig.parameters) == 1
    assert sig.parameters["arg"].annotation is str


def test_get_typed_signature_two_params() -> None:
    def my_function(arg: str, arg2: int) -> None:
        return None

    sig = get_typed_signature(my_function)
    assert isinstance(sig, inspect.Signature)
    assert len(sig.parameters) == 2
    assert sig.parameters["arg"].annotation is str
    assert sig.parameters["arg2"].annotation is int


def test_get_typed_signature_param_str() -> None:
    def my_function(arg: "str") -> None:
        return None

    sig = get_typed_signature(my_function)
    assert isinstance(sig, inspect.Signature)
    assert len(sig.parameters) == 1
    assert sig.parameters["arg"].annotation is str


def test_get_typed_signature_param_annotated() -> None:
    def my_function(arg: Annotated[str, "An arg"]) -> None:
        return None

    sig = get_typed_signature(my_function)
    assert isinstance(sig, inspect.Signature)
    assert len(sig.parameters) == 1
    assert sig.parameters["arg"].annotation == Annotated[str, "An arg"]


def test_func_tool() -> None:
    def my_function() -> str:
        return "result"

    tool = FunctionTool(my_function, description="Function tool.")
    assert tool.name == "my_function"
    assert tool.description == "Function tool."
    assert issubclass(tool.args_type(), BaseModel)
    assert issubclass(tool.return_type(), str)
    assert tool.state_type() is None


def test_func_tool_annotated_arg() -> None:
    def my_function(my_arg: Annotated[str, "test description"]) -> str:
        return "result"

    tool = FunctionTool(my_function, description="Function tool.")
    assert tool.name == "my_function"
    assert tool.description == "Function tool."
    assert issubclass(tool.args_type(), BaseModel)
    assert issubclass(tool.return_type(), str)
    assert tool.args_type().model_fields["my_arg"].description == "test description"
    assert tool.args_type().model_fields["my_arg"].annotation is str
    assert tool.args_type().model_fields["my_arg"].is_required() is True
    assert tool.args_type().model_fields["my_arg"].default is PydanticUndefined
    assert len(tool.args_type().model_fields) == 1
    assert tool.return_type() is str
    assert tool.state_type() is None


def test_func_tool_return_annotated() -> None:
    def my_function() -> Annotated[str, "test description"]:
        return "result"

    tool = FunctionTool(my_function, description="Function tool.")
    assert tool.name == "my_function"
    assert tool.description == "Function tool."
    assert issubclass(tool.args_type(), BaseModel)
    assert tool.return_type() is str
    assert tool.state_type() is None


def test_func_tool_no_args() -> None:
    def my_function() -> str:
        return "result"

    tool = FunctionTool(my_function, description="Function tool.")
    assert tool.name == "my_function"
    assert tool.description == "Function tool."
    assert issubclass(tool.args_type(), BaseModel)
    assert len(tool.args_type().model_fields) == 0
    assert tool.return_type() is str
    assert tool.state_type() is None


def test_func_tool_return_none() -> None:
    def my_function() -> None:
        return None

    tool = FunctionTool(my_function, description="Function tool.")
    assert tool.name == "my_function"
    assert tool.description == "Function tool."
    assert issubclass(tool.args_type(), BaseModel)
    assert tool.return_type() is type(None)
    assert tool.state_type() is None


def test_func_tool_return_base_model() -> None:
    def my_function() -> MyResult:
        return MyResult(result="value")

    tool = FunctionTool(my_function, description="Function tool.")
    assert tool.name == "my_function"
    assert tool.description == "Function tool."
    assert issubclass(tool.args_type(), BaseModel)
    assert tool.return_type() is MyResult
    assert tool.state_type() is None


@pytest.mark.asyncio
async def test_func_call_tool() -> None:
    def my_function() -> str:
        return "result"

    tool = FunctionTool(my_function, description="Function tool.")
    result = await tool.run_json({}, CancellationToken())
    assert result == "result"


@pytest.mark.asyncio
async def test_func_call_tool_base_model() -> None:
    def my_function() -> MyResult:
        return MyResult(result="value")

    tool = FunctionTool(my_function, description="Function tool.")
    result = await tool.run_json({}, CancellationToken())
    assert isinstance(result, MyResult)
    assert result.result == "value"


@pytest.mark.asyncio
async def test_func_call_tool_with_arg_base_model() -> None:
    def my_function(arg: str) -> MyResult:
        return MyResult(result="value")

    tool = FunctionTool(my_function, description="Function tool.")
    result = await tool.run_json({"arg": "test"}, CancellationToken())
    assert isinstance(result, MyResult)
    assert result.result == "value"


@pytest.mark.asyncio
async def test_func_str_res() -> None:
    def my_function(arg: str) -> str:
        return "test"

    tool = FunctionTool(my_function, description="Function tool.")
    result = await tool.run_json({"arg": "test"}, CancellationToken())
    assert tool.return_value_as_string(result) == "test"


@pytest.mark.asyncio
async def test_func_base_model_res() -> None:
    def my_function(arg: str) -> MyResult:
        return MyResult(result="test")

    tool = FunctionTool(my_function, description="Function tool.")
    result = await tool.run_json({"arg": "test"}, CancellationToken())
    assert tool.return_value_as_string(result) == '{"result": "test"}'


@pytest.mark.asyncio
async def test_func_base_model_custom_dump_res() -> None:
    class MyResultCustomDump(BaseModel):
        result: str = Field(description="The other description.")

        @model_serializer
        def ser_model(self) -> str:
            return "custom: " + self.result

    def my_function(arg: str) -> MyResultCustomDump:
        return MyResultCustomDump(result="test")

    tool = FunctionTool(my_function, description="Function tool.")
    result = await tool.run_json({"arg": "test"}, CancellationToken())
    assert tool.return_value_as_string(result) == "custom: test"


@pytest.mark.asyncio
async def test_func_int_res() -> None:
    def my_function(arg: int) -> int:
        return arg

    tool = FunctionTool(my_function, description="Function tool.")
    result = await tool.run_json({"arg": 5}, CancellationToken())
    assert tool.return_value_as_string(result) == "5"


@pytest.mark.asyncio
async def test_func_tool_return_list() -> None:
    def my_function() -> List[int]:
        return [1, 2]

    tool = FunctionTool(my_function, description="Function tool.")
    result = await tool.run_json({}, CancellationToken())
    assert isinstance(result, list)
    assert result == [1, 2]
    assert tool.return_value_as_string(result) == "[1, 2]"


def test_nested_tool_schema_generation() -> None:
    schema: ToolSchema = MyNestedTool().schema

    assert "description" in schema
    assert "parameters" in schema
    assert "type" in schema["parameters"]
    assert "arg" in schema["parameters"]["properties"]
    assert "type" in schema["parameters"]["properties"]["arg"]
    assert "title" in schema["parameters"]["properties"]["arg"]
    assert "properties" in schema["parameters"]["properties"]["arg"]
    assert "query" in schema["parameters"]["properties"]["arg"]["properties"]
    assert "type" in schema["parameters"]["properties"]["arg"]["properties"]["query"]
    assert "description" in schema["parameters"]["properties"]["arg"]["properties"]["query"]
    assert "required" in schema["parameters"]
    assert schema["description"] == "Description of test nested tool."
    assert schema["parameters"]["type"] == "object"
    assert schema["parameters"]["properties"]["arg"]["type"] == "object"
    assert schema["parameters"]["properties"]["arg"]["title"] == "MyArgs"
    assert schema["parameters"]["properties"]["arg"]["properties"]["query"]["type"] == "string"
    assert schema["parameters"]["properties"]["arg"]["properties"]["query"]["description"] == "The description."
    assert schema["parameters"]["properties"]["arg"]["required"] == ["query"]
    assert schema["parameters"]["required"] == ["arg"]
    assert len(schema["parameters"]["properties"]) == 1


@pytest.mark.asyncio
async def test_nested_tool_run() -> None:
    tool = MyNestedTool()
    result = await tool.run_json({"arg": {"query": "test"}}, CancellationToken())

    assert isinstance(result, MyResult)
    assert result.result == "value"
    assert tool.called_count == 1

    result = await tool.run_json({"arg": {"query": "test"}}, CancellationToken())
    result = await tool.run_json({"arg": {"query": "test"}}, CancellationToken())

    assert tool.called_count == 3


def test_nested_tool_properties() -> None:
    tool = MyNestedTool()

    assert tool.name == "TestNestedTool"
    assert tool.description == "Description of test nested tool."
    assert tool.args_type() == MyNestedArgs
    assert tool.return_type() == MyResult
    assert tool.state_type() is None


# --- Define a sample Pydantic model and tool function ---


class AddInput(BaseModel):
    x: int
    y: int


def add_tool(input: AddInput) -> int:
    return input.x + input.y


@pytest.mark.asyncio
async def test_func_tool_with_pydantic_model_conversion_success() -> None:
    tool = FunctionTool(add_tool, description="Tool to add two numbers.")
    test_input = {"input": {"x": 2, "y": 3}}
    result = await tool.run_json(test_input, CancellationToken())

    assert result == 5
    assert tool.return_value_as_string(result) == "5"


@pytest.mark.asyncio
async def test_func_tool_with_pydantic_model_conversion_failure() -> None:
    tool = FunctionTool(add_tool, description="Tool to add two numbers.")
    test_input = {"input": {"x": 2}}

    with pytest.raises(ValidationError, match="Field required"):
        await tool.run_json(test_input, CancellationToken())


# --- Additional test using a dataclass ---
@dataclass
class MultiplyInput:
    a: int
    b: int


def multiply_tool(input: MultiplyInput) -> int:
    return input.a * input.b


@pytest.mark.asyncio
async def test_func_tool_with_dataclass_conversion_success() -> None:
    tool = FunctionTool(multiply_tool, description="Tool to multiply two numbers.")
    test_input = {"input": {"a": 4, "b": 5}}
    result = await tool.run_json(test_input, CancellationToken())
    assert result == 20
    assert tool.return_value_as_string(result) == "20"


@pytest.mark.asyncio
async def test_func_tool_with_dataclass_conversion_failure() -> None:
    tool = FunctionTool(multiply_tool, description="Tool to multiply two numbers.")
    # Missing field 'b'
    test_input = {"input": {"a": 4}}

    with pytest.raises(ValidationError, match="Field required"):
        await tool.run_json(test_input, CancellationToken())


# Guardrail provider implementations for testing.


class _AllowGuardrail:
    """A guardrail that always allows."""

    async def evaluate(
        self,
        *,
        tool_name: str,
        args: Mapping[str, Any],
        agent_name: str | None = None,
        call_id: str | None = None,
        cancellation_token: Any = None,
    ) -> GuardrailResult:
        return GuardrailResult(decision=Decision.ALLOW)


class _DenyGuardrail:
    """A guardrail that always denies with a configurable reason."""

    def __init__(self, reason: str | None = "denied by test guardrail"):
        self._reason = reason

    async def evaluate(
        self,
        *,
        tool_name: str,
        args: Mapping[str, Any],
        agent_name: str | None = None,
        call_id: str | None = None,
        cancellation_token: Any = None,
    ) -> GuardrailResult:
        return GuardrailResult(decision=Decision.DENY, reason=self._reason)


class _ModifyGuardrail:
    """A guardrail that modifies arguments."""

    def __init__(self, override: Mapping[str, Any]):
        self._override = override

    async def evaluate(
        self,
        *,
        tool_name: str,
        args: Mapping[str, Any],
        agent_name: str | None = None,
        call_id: str | None = None,
        cancellation_token: Any = None,
    ) -> GuardrailResult:
        return GuardrailResult(
            decision=Decision.MODIFY,
            modified_args=self._override,
            reason="args modified by test guardrail",
        )


class _CountingGuardrail:
    """A guardrail that counts how many times it was called."""

    def __init__(self) -> None:
        self.call_count = 0
        self.last_tool_name: str | None = None
        self.last_args: Mapping[str, Any] | None = None

    async def evaluate(
        self,
        *,
        tool_name: str,
        args: Mapping[str, Any],
        agent_name: str | None = None,
        call_id: str | None = None,
        cancellation_token: Any = None,
    ) -> GuardrailResult:
        self.call_count += 1
        self.last_tool_name = tool_name
        self.last_args = dict(args)
        return GuardrailResult(decision=Decision.ALLOW)


# ---------------------------------------------------------------------------
# Tests for guardrail integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_guardrail_protocol_allow() -> None:
    """A tool with an allow guardrail executes normally."""
    tool = MyTool()
    tool.add_guardrail(_AllowGuardrail())

    result = await tool.run_json({"query": "test"}, CancellationToken())

    assert result.result == "value"
    assert tool.called_count == 1


@pytest.mark.asyncio
async def test_guardrail_allow_executes() -> None:
    """When the guardrail returns ALLOW, the tool runs normally."""
    tool = MyTool()
    tool.add_guardrail(_AllowGuardrail())
    result = await tool.run_json({"query": "test"}, CancellationToken())
    assert result.result == "value"


@pytest.mark.asyncio
async def test_guardrail_deny_returns_denial_string() -> None:
    """When the guardrail returns DENY, the tool does not execute and raises a structured denial."""
    tool = MyTool()
    tool.add_guardrail(_DenyGuardrail("unsafe input"))
    with pytest.raises(GuardrailDeniedError, match="unsafe input"):
        await tool.run_json({"query": "test"}, CancellationToken())
    assert tool.called_count == 0


@pytest.mark.asyncio
async def test_guardrail_deny_preserves_reason() -> None:
    """DENY without a reason falls back to 'policy violation'."""
    tool = MyTool()
    tool.add_guardrail(_DenyGuardrail(None))
    with pytest.raises(GuardrailDeniedError, match="policy violation"):
        await tool.run_json({"query": "test"}, CancellationToken())
    assert tool.called_count == 0


@pytest.mark.asyncio
async def test_guardrail_modify_passes_modified_args() -> None:
    """When the guardrail returns MODIFY, the tool receives the modified arguments."""
    tool = RecordingTool()
    tool.add_guardrail(_ModifyGuardrail({"query": "modified input"}))
    result = await tool.run_json({"query": "original"}, CancellationToken())
    assert result.result == "modified input"
    assert tool.last_args == MyArgs(query="modified input")


@pytest.mark.asyncio
async def test_guardrail_chain_order() -> None:
    """Guardrails evaluate in order; first DENY short-circuits."""
    tool = MyTool()
    counter = _CountingGuardrail()
    tool.add_guardrail(_DenyGuardrail("stop here"))
    tool.add_guardrail(counter)  # Should never be reached

    with pytest.raises(GuardrailDeniedError, match="stop here"):
        await tool.run_json({"query": "test"}, CancellationToken())
    assert counter.call_count == 0  # never called


@pytest.mark.asyncio
async def test_guardrail_chain_all_allow() -> None:
    """When all guardrails return ALLOW, the tool executes."""
    tool = MyTool()
    counter = _CountingGuardrail()
    tool.add_guardrail(_CountingGuardrail())
    tool.add_guardrail(counter)

    result = await tool.run_json({"query": "test"}, CancellationToken())
    assert result.result == "value"
    assert counter.call_count == 1


@pytest.mark.asyncio
async def test_guardrail_modify_chains() -> None:
    """MODIFY passes modified args to the next guardrail in the chain."""
    tool = MyTool()
    second = _CountingGuardrail()
    tool.add_guardrail(_ModifyGuardrail({"query": "first pass"}))
    tool.add_guardrail(second)

    await tool.run_json({"query": "original"}, CancellationToken())
    # The second guardrail receives the modified args
    assert second.last_args == {"query": "first pass"}


@pytest.mark.asyncio
async def test_guardrail_receives_tool_name() -> None:
    """Guardrail receives the correct tool name."""
    tool = MyTool()
    counter = _CountingGuardrail()
    tool.add_guardrail(counter)

    await tool.run_json({"query": "test"}, CancellationToken())
    assert counter.last_tool_name == "TestTool"


@pytest.mark.asyncio
async def test_guardrail_receives_original_args() -> None:
    """Guardrail receives the arguments as passed (not yet modified by earlier guardrails in the chain)."""
    tool = MyTool()
    counter = _CountingGuardrail()
    tool.add_guardrail(_ModifyGuardrail({"query": "modified"}))
    tool.add_guardrail(counter)

    await tool.run_json({"query": "original"}, CancellationToken())
    # First guardrail modified to "modified", but second guardrail receives
    # what was passed to it by the first guardrail (the MODIFY result)
    assert counter.last_args == {"query": "modified"}


@pytest.mark.asyncio
async def test_guardrail_multiple_tools_independent() -> None:
    """Each tool instance has its own guardrail chain."""
    tool_a = MyTool()
    tool_b = MyTool()
    counter_a = _CountingGuardrail()
    counter_b = _CountingGuardrail()
    tool_a.add_guardrail(counter_a)
    tool_b.add_guardrail(counter_b)

    await tool_a.run_json({"query": "a"}, CancellationToken())
    await tool_b.run_json({"query": "b"}, CancellationToken())
    await tool_b.run_json({"query": "c"}, CancellationToken())

    assert counter_a.call_count == 1
    assert counter_b.call_count == 2


@pytest.mark.asyncio
async def test_guardrail_via_init() -> None:
    """GuardrailProvider can be passed at construction time via BaseTool.__init__."""

    async def typed_query(query: str) -> str:
        return query

    counter = _CountingGuardrail()
    tool = FunctionTool(
        typed_query,
        description="Example",
        guardrail_providers=(_AllowGuardrail(), counter),
    )

    result = await tool.run_json({"query": "test"}, CancellationToken())

    assert result == "test"
    assert counter.call_count == 1


@pytest.mark.asyncio
async def test_guardrail_empty_chain_no_overhead() -> None:
    """A tool with no guardrails executes without any guardrail overhead."""
    tool = MyTool()
    result = await tool.run_json({"query": "test"}, CancellationToken())
    assert result.result == "value"


@pytest.mark.asyncio
async def test_guardrail_deny_preserves_tool_error_behavior() -> None:
    """Guardrail DENY raises a structured error without calling the tool."""
    tool = MyTool()
    tool.add_guardrail(_DenyGuardrail("custom reason"))

    with pytest.raises(GuardrailDeniedError, match="custom reason"):
        await tool.run_json({"query": "test"}, CancellationToken())
    assert tool.called_count == 0


@pytest.mark.asyncio
async def test_guardrail_deny_logs_terminal_event(caplog: pytest.LogCaptureFixture) -> None:
    """DENY is traced through the normal tool-call logging path without executing the tool."""
    tool = MyTool()
    tool.add_guardrail(_DenyGuardrail("blocked by policy"))
    caplog.set_level(logging.INFO, logger=EVENT_LOGGER_NAME)

    with pytest.raises(GuardrailDeniedError, match="blocked by policy"):
        await tool.run_json({"query": "secret"}, CancellationToken(), call_id="call-1")

    events = [json.loads(record.getMessage()) for record in caplog.records]
    assert events[-1]["type"] == "ToolCall"
    assert events[-1]["tool_name"] == "TestTool"
    assert events[-1]["arguments"] == {"query": "secret"}
    assert "blocked by policy" in events[-1]["result"]


@pytest.mark.asyncio
async def test_guardrail_modify_logs_effective_args(caplog: pytest.LogCaptureFixture) -> None:
    """MODIFY logs the same arguments that are actually passed to the tool."""
    tool = RecordingTool()
    tool.add_guardrail(_ModifyGuardrail({"query": "effective"}))
    caplog.set_level(logging.INFO, logger=EVENT_LOGGER_NAME)

    result = await tool.run_json({"query": "original"}, CancellationToken())

    events = [json.loads(record.getMessage()) for record in caplog.records]
    assert result.result == "effective"
    assert events[-1]["arguments"] == {"query": "effective"}
    assert events[-1]["result"] == '{"result": "effective"}'


@pytest.mark.asyncio
async def test_guardrail_stream_deny_raises_without_yielding_string() -> None:
    """Streaming tools use the same structured denial path as run_json."""
    tool = MyStreamTool()
    tool.add_guardrail(_DenyGuardrail("stream blocked"))

    with pytest.raises(GuardrailDeniedError, match="stream blocked"):
        _ = [item async for item in tool.run_json_stream({"query": "test"}, CancellationToken())]

    assert tool.called_count == 0


@pytest.mark.asyncio
async def test_guardrail_stream_modify_passes_effective_args() -> None:
    """Streaming tools execute with modified arguments after revalidation."""
    tool = MyStreamTool()
    tool.add_guardrail(_ModifyGuardrail({"query": "stream effective"}))

    results = [item async for item in tool.run_json_stream({"query": "stream original"}, CancellationToken())]

    assert [item.result for item in results] == ["stream effective"]


def test_guardrail_public_import_path() -> None:
    from autogen_core.tools import Decision as PublicDecision
    from autogen_core.tools import GuardrailDeniedError as PublicGuardrailDeniedError
    from autogen_core.tools import GuardrailProvider as PublicGuardrailProvider
    from autogen_core.tools import GuardrailResult as PublicGuardrailResult

    assert PublicDecision is Decision
    assert PublicGuardrailDeniedError is GuardrailDeniedError
    assert PublicGuardrailProvider is GuardrailProvider
    assert PublicGuardrailResult is GuardrailResult


@pytest.mark.asyncio
async def test_guardrail_guardrail_provider_subclass() -> None:
    """GuardrailProvider is a runtime-checkable Protocol."""

    class SubclassGuardrail:
        async def evaluate(
            self,
            *,
            tool_name: str,
            args: Mapping[str, Any],
            agent_name: str | None = None,
            call_id: str | None = None,
            cancellation_token: Any = None,
        ) -> GuardrailResult:
            return GuardrailResult(decision=Decision.ALLOW)

    guardrail = SubclassGuardrail()
    assert isinstance(guardrail, GuardrailProvider)
    tool = MyTool()
    tool.add_guardrail(guardrail)

    result = await tool.run_json({"query": "test"}, CancellationToken())

    assert result.result == "value"
