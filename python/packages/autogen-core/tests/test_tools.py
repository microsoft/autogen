import inspect
from functools import partial
from typing import Annotated, List

import pytest
from autogen_core import CancellationToken
from autogen_core._function_utils import get_typed_signature
from autogen_core.tools import BaseTool, FunctionTool
from autogen_core.tools._base import ToolSchema
from pydantic import BaseModel, Field, model_serializer
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
