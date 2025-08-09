import inspect
from dataclasses import dataclass
from functools import partial
from typing import Annotated, Any, AsyncGenerator, List

import pytest
from autogen_core import CancellationToken
from autogen_core._function_utils import get_typed_signature
from autogen_core.tools import BaseTool, FunctionTool
from autogen_core.tools._base import BaseCustomTool, BaseStreamTool, BaseToolWithState, ToolSchema
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

        @model_serializer(mode="plain")
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


# Tests for BaseStreamTool
class StreamArgs(BaseModel):
    count: int = Field(description="Number of items to stream")


class StreamResult(BaseModel):
    final_count: int = Field(description="Final count")


class StreamItem(BaseModel):
    item: int = Field(description="Stream item")


class SampleStreamTool(BaseStreamTool[StreamArgs, StreamItem, StreamResult]):
    def __init__(self) -> None:
        super().__init__(
            args_type=StreamArgs,
            return_type=StreamResult,
            name="TestStreamTool",
            description="A test stream tool",
        )

    async def run(self, args: StreamArgs, cancellation_token: CancellationToken) -> StreamResult:
        return StreamResult(final_count=args.count)

    async def run_stream(
        self, args: StreamArgs, cancellation_token: CancellationToken
    ) -> AsyncGenerator[StreamItem | StreamResult, None]:
        for i in range(args.count):
            yield StreamItem(item=i)
        yield StreamResult(final_count=args.count)


@pytest.mark.asyncio
async def test_stream_tool_run_json_stream() -> None:
    tool = SampleStreamTool()
    results: list[Any] = []
    async for result in tool.run_json_stream({"count": 3}, CancellationToken()):
        results.append(result)

    assert len(results) == 4  # 3 stream items + 1 final result
    assert isinstance(results[0], StreamItem)
    assert isinstance(results[1], StreamItem)
    assert isinstance(results[2], StreamItem)
    assert isinstance(results[3], StreamResult)
    assert results[3].final_count == 3


@pytest.mark.asyncio
async def test_stream_tool_error_no_final_return() -> None:
    class BadStreamTool(BaseStreamTool[StreamArgs, StreamItem, StreamResult]):
        def __init__(self) -> None:
            super().__init__(
                args_type=StreamArgs,
                return_type=StreamResult,
                name="BadStreamTool",
                description="A bad test stream tool",
            )

        async def run(self, args: StreamArgs, cancellation_token: CancellationToken) -> StreamResult:
            return StreamResult(final_count=args.count)

        async def run_stream(
            self, args: StreamArgs, cancellation_token: CancellationToken
        ) -> AsyncGenerator[StreamItem | StreamResult, None]:
            # This doesn't yield anything - should raise assertion error
            return
            yield  # unreachable

    tool = BadStreamTool()
    with pytest.raises(AssertionError, match="The tool must yield a final return value"):
        async for _result in tool.run_json_stream({"count": 1}, CancellationToken()):
            pass


@pytest.mark.asyncio
async def test_stream_tool_error_wrong_return_type() -> None:
    class WrongReturnStreamTool(BaseStreamTool[StreamArgs, StreamItem, StreamResult]):
        def __init__(self) -> None:
            super().__init__(
                args_type=StreamArgs,
                return_type=StreamResult,
                name="WrongReturnStreamTool",
                description="A wrong return type stream tool",
            )

        async def run(self, args: StreamArgs, cancellation_token: CancellationToken) -> StreamResult:
            return StreamResult(final_count=args.count)

        async def run_stream(
            self, args: StreamArgs, cancellation_token: CancellationToken
        ) -> AsyncGenerator[StreamItem | StreamResult, None]:
            yield StreamItem(item=0)
            yield StreamItem(item=1)  # Wrong final type

    tool = WrongReturnStreamTool()
    with pytest.raises(TypeError, match="Expected return value of type StreamResult"):
        async for _result in tool.run_json_stream({"count": 1}, CancellationToken()):
            pass


# Tests for BaseToolWithState
class StateArgs(BaseModel):
    value: str = Field(description="Value to store")


class StateResult(BaseModel):
    stored_value: str = Field(description="The stored value")


class ToolState(BaseModel):
    internal_value: str = Field(description="Internal state")


class SampleToolWithState(BaseToolWithState[StateArgs, StateResult, ToolState]):
    def __init__(self) -> None:
        super().__init__(
            args_type=StateArgs,
            return_type=StateResult,
            state_type=ToolState,
            name="TestToolWithState",
            description="A test tool with state",
        )
        self.state = ToolState(internal_value="initial")

    async def run(self, args: StateArgs, cancellation_token: CancellationToken) -> StateResult:
        self.state.internal_value = args.value
        return StateResult(stored_value=self.state.internal_value)

    def save_state(self) -> ToolState:
        return self.state

    def load_state(self, state: ToolState) -> None:
        self.state = state

    def state_type(self) -> type[ToolState]:
        return ToolState


@pytest.mark.asyncio
async def test_tool_with_state_save_load() -> None:
    tool = SampleToolWithState()

    # Set some state
    await tool.run_json({"value": "test_state"}, CancellationToken())

    # Save state
    saved_state = await tool.save_state_json()
    assert saved_state == {"internal_value": "test_state"}

    # Create new tool and load state
    new_tool = SampleToolWithState()
    await new_tool.load_state_json(saved_state)

    # Verify state was loaded
    assert new_tool.state.internal_value == "test_state"


# Tests for BaseCustomTool


class CustomResult(BaseModel):
    processed: str = Field(description="Processed input")


class SampleCustomTool(BaseCustomTool[CustomResult]):
    def __init__(self) -> None:
        super().__init__(
            return_type=CustomResult,
            name="SampleCustomTool",
            description="A test custom tool",
        )

    async def run(self, input_text: str, cancellation_token: CancellationToken) -> CustomResult:
        return CustomResult(processed=f"processed: {input_text}")


@pytest.mark.asyncio
async def test_custom_tool_run_freeform() -> None:
    tool = SampleCustomTool()
    result = await tool.run_freeform("test input", CancellationToken())

    assert isinstance(result, CustomResult)
    assert result.processed == "processed: test input"


def test_custom_tool_schema() -> None:
    tool = SampleCustomTool()
    schema = tool.schema

    assert schema["name"] == "SampleCustomTool"
    assert schema.get("description") == "A test custom tool"
    assert "format" not in schema


def test_custom_tool_schema_with_format() -> None:
    from autogen_core.tools._base import CustomToolFormat

    format_spec = CustomToolFormat(type="grammar", syntax="lark", definition="start: WORD")

    class CustomToolWithFormat(BaseCustomTool[BaseModel]):
        def __init__(self) -> None:
            from pydantic import BaseModel

            class Result(BaseModel):
                text: str

            super().__init__(
                return_type=Result,
                name="FormattedTool",
                description="Tool with format",
                format=format_spec,
            )

        async def run(self, input_text: str, cancellation_token: CancellationToken) -> BaseModel:
            from pydantic import BaseModel

            class Result(BaseModel):
                text: str

            return Result(text=input_text)

    tool = CustomToolWithFormat()
    schema = tool.schema

    assert schema["name"] == "FormattedTool"
    assert schema.get("format") == format_spec


def test_custom_tool_properties() -> None:
    tool = SampleCustomTool()

    assert tool.name == "SampleCustomTool"
    assert tool.description == "A test custom tool"
    assert tool.return_type() == CustomResult


def test_custom_tool_return_value_as_string() -> None:
    tool = SampleCustomTool()

    # Test with BaseModel
    result = CustomResult(processed="test")
    assert tool.return_value_as_string(result) == '{"processed": "test"}'

    # Test with non-BaseModel
    assert tool.return_value_as_string("simple string") == "simple string"
    assert tool.return_value_as_string(42) == "42"


@pytest.mark.asyncio
async def test_custom_tool_save_load_state() -> None:
    tool = SampleCustomTool()

    # Default implementations should return empty dict and do nothing
    saved_state = await tool.save_state_json()
    assert saved_state == {}

    # Load should not raise error
    await tool.load_state_json({"some": "state"})


# Tests for strict mode validation errors
def test_strict_mode_additional_properties_error() -> None:
    from pydantic import ConfigDict

    class StrictArgsWithAdditional(BaseModel):
        model_config = ConfigDict(extra="allow")
        required_field: str = Field(description="Required field")

    class StrictToolWithAdditional(BaseTool[StrictArgsWithAdditional, MyResult]):
        def __init__(self) -> None:
            super().__init__(
                args_type=StrictArgsWithAdditional,
                return_type=MyResult,
                name="StrictTestTool",
                description="Tool with additional properties",
                strict=True,
            )

        async def run(self, args: StrictArgsWithAdditional, cancellation_token: CancellationToken) -> MyResult:
            return MyResult(result="value")

    with pytest.raises(ValueError, match="Strict mode is enabled but additional argument is also enabled"):
        tool = StrictToolWithAdditional()
        _ = tool.schema


# Test return_value_as_string edge cases
def test_return_value_as_string_edge_cases() -> None:
    tool = MyTool()

    # Test with BaseModel that dumps to non-dict (custom serializer)
    class NonDictModel(BaseModel):
        value: str

        @model_serializer(mode="plain")
        def ser_model(self) -> str:
            return self.value

    model = NonDictModel(value="test")
    assert tool.return_value_as_string(model) == "test"

    # Test with None
    assert tool.return_value_as_string(None) == "None"

    # Test with list
    assert tool.return_value_as_string([1, 2, 3]) == "[1, 2, 3]"


# Test state_type method for regular BaseTool
def test_base_tool_state_type() -> None:
    tool = MyTool()
    assert tool.state_type() is None


# Test save/load state methods for regular BaseTool
@pytest.mark.asyncio
async def test_base_tool_default_state_methods() -> None:
    tool = MyTool()

    # Default save should return empty dict
    saved_state = await tool.save_state_json()
    assert saved_state == {}

    # Default load should not raise error
    await tool.load_state_json({"some": "state"})
