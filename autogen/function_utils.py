import inspect
from typing import get_type_hints, Callable, Any, Dict, Union, List, Optional, Type
from typing_extensions import Annotated, Literal

from pydantic import BaseModel, Field
from .pydantic import type2schema, JsonSchemaValue, model_dump


class Parameters(BaseModel):
    """Parameters of a function as defined by the OpenAI API"""

    type: Literal["object"] = "object"
    properties: Dict[str, JsonSchemaValue]
    required: List[str]


class Function(BaseModel):
    """A function as defined by the OpenAI API"""

    description: Annotated[str, Field(description="Description of the function")]
    name: Annotated[str, Field(description="Name of the function")]
    parameters: Annotated[Parameters, Field(description="Parameters of the function")]


def get_parameter_json_schema(k: str, v: Union[Annotated[Any, str], Type]) -> JsonSchemaValue:
    """Get a JSON schema for a parameter as defined by the OpenAI API

    Args:
        k: The name of the parameter
        v: The type of the parameter

    Returns:
        A Pydanitc model for the parameter
    """

    def type2description(k: str, v: Union[Annotated[Any, str], Type]) -> str:
        if hasattr(v, "__metadata__"):
            return v.__metadata__[0]
        else:
            return k

    schema = type2schema(v)
    schema["description"] = type2description(k, v)

    return schema


def get_required_params(signature: inspect.Signature) -> List[str]:
    """Get the required parameters of a function

    Args:
        signature: The signature of the function as returned by inspect.signature

    Returns:
        A list of the required parameters of the function
    """
    return [k for k, v in signature.parameters.items() if v.default == inspect._empty]


def get_parameters(required: List[str], hints: Dict[str, Union[Annotated[Any, str], Type]]) -> Parameters:
    """Get the parameters of a function as defined by the OpenAI API

    Args:
        required: The required parameters of the function
        hints: The type hints of the function as returned by typing.get_type_hints

    Returns:
        A Pydantic model for the parameters of the function
    """
    return Parameters(
        properties={k: get_parameter_json_schema(k, v) for k, v in hints.items() if k != "return"}, required=required
    )


def get_function_schema(f: Callable[..., Any], *, name: Optional[str] = None, description: str) -> Dict[str, Any]:
    """Get a JSON schema for a function as defined by the OpenAI API

    Args:
        f: The function to get the JSON schema for
        name: The name of the function
        description: The description of the function

    Returns:
        A JSON schema for the function

    Raises:
        TypeError: If the function is not annotated

    Examples:
        ```
        def f(a: Annotated[str, "Parameter a"], b: int = 2, c: Annotated[float, "Parameter c"] = 0.1) -> None:
            pass

        get_function(f, description="function f")
        # {'type': 'function', 'function': {'description': 'function f', 'name': 'f', 'parameters': {'type': 'object', 'properties': {'a': {'type': 'str', 'description': 'Parameter a'}, 'b': {'type': 'int', 'description': 'b'}, 'c': {'type': 'float', 'description': 'Parameter c'}}, 'required': ['a']}}}
        ```

    """
    signature = inspect.signature(f)
    hints = get_type_hints(f, include_extras=True)

    if set(signature.parameters.keys()).union({"return"}) != set(hints.keys()).union({"return"}):
        missing = [f"'{x}'" for x in set(signature.parameters.keys()) - set(hints.keys())]
        raise TypeError(
            f"All parameters of a function '{f.__name__}' must be annotated. The annotations are missing for parameters: {', '.join(missing)}"
        )

    fname = name if name else f.__name__

    required = get_required_params(signature)

    parameters = get_parameters(required, hints)

    function = Function(
        description=description,
        name=fname,
        parameters=parameters,
    )

    return model_dump(function)
