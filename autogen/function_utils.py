import inspect
from typing import get_type_hints, Callable, Any, Dict, Union, List, Optional, Type, ForwardRef
from typing_extensions import Annotated, Literal

from pydantic import BaseModel, Field
from .pydantic import type2schema, JsonSchemaValue, evaluate_forwardref, model_dump


def get_typed_annotation(annotation: Any, globalns: Dict[str, Any]) -> Any:
    """Get the type annotation of a parameter.

    Args:
        annotation: The annotation of the parameter
        globalns: The global namespace of the function

    Returns:
        The type annotation of the parameter
    """
    if isinstance(annotation, str):
        annotation = ForwardRef(annotation)
        annotation = evaluate_forwardref(annotation, globalns, globalns)
    return annotation


def get_typed_signature(call: Callable[..., Any]) -> inspect.Signature:
    """Get the signature of a function with type annotations.

    Args:
        call: The function to get the signature for

    Returns:
        The signature of the function with type annotations
    """
    signature = inspect.signature(call)
    globalns = getattr(call, "__globals__", {})
    typed_params = [
        inspect.Parameter(
            name=param.name,
            kind=param.kind,
            default=param.default,
            annotation=get_typed_annotation(param.annotation, globalns),
        )
        for param in signature.parameters.values()
    ]
    typed_signature = inspect.Signature(typed_params)
    return typed_signature


def get_typed_return_annotation(call: Callable[..., Any]) -> Any:
    """Get the return annotation of a function.

    Args:
        call: The function to get the return annotation for

    Returns:
        The return annotation of the function
    """
    signature = inspect.signature(call)
    annotation = signature.return_annotation

    if annotation is inspect.Signature.empty:
        return None

    globalns = getattr(call, "__globals__", {})
    return get_typed_annotation(annotation, globalns)


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


def get_parameter_json_schema(k: str, v: Union[Annotated[Type, str], Type]) -> JsonSchemaValue:
    """Get a JSON schema for a parameter as defined by the OpenAI API

    Args:
        k: The name of the parameter
        v: The type of the parameter

    Returns:
        A Pydanitc model for the parameter
    """

    def type2description(k: str, v: Union[Annotated[Type, str], Type]) -> str:
        if hasattr(v, "__metadata__"):
            return v.__metadata__[0]
        else:
            return k

    schema = type2schema(v)
    schema["description"] = type2description(k, v)

    return schema


def get_required_params(typed_signature: inspect.Signature) -> List[str]:
    """Get the required parameters of a function

    Args:
        signature: The signature of the function as returned by inspect.signature

    Returns:
        A list of the required parameters of the function
    """
    return [k for k, v in typed_signature.parameters.items() if v.default == inspect.Signature.empty]


def get_parameters(required: List[str], param_annotations: Dict[str, Union[Annotated[Type, str], Type]]) -> Parameters:
    """Get the parameters of a function as defined by the OpenAI API

    Args:
        required: The required parameters of the function
        hints: The type hints of the function as returned by typing.get_type_hints

    Returns:
        A Pydantic model for the parameters of the function
    """
    return Parameters(
        properties={k: get_parameter_json_schema(k, v) for k, v in param_annotations.items() if k != "return"},
        required=required,
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

        get_function_schema(f, description="function f")

        #   {'type': 'function',
        #    'function': {'description': 'function f',
        #        'name': 'f',
        #        'parameters': {'type': 'object',
        #           'properties': {'a': {'type': 'str', 'description': 'Parameter a'},
        #               'b': {'type': 'int', 'description': 'b'},
        #               'c': {'type': 'float', 'description': 'Parameter c'}},
        #           'required': ['a']}}}
            ```

    """
    typed_signature = get_typed_signature(f)
    param_annotations = {k: v.annotation for k, v in typed_signature.parameters.items()}
    return_annotation = get_typed_return_annotation(f)
    missing_annotations = [k for k, v in param_annotations.items() if v is inspect.Signature.empty]

    if return_annotation is None:
        raise TypeError(
            "The return type of a function must be annotated as either 'str', a subclass of "
            + "'pydantic.BaseModel' or an union of the previous ones."
        )

    if missing_annotations != []:
        [f"'{k}'" for k in missing_annotations]
        raise TypeError(
            f"All parameters of a function '{f.__name__}' must be annotated. "
            + "The annotations are missing for parameters: {', '.join(missing)}"
        )

    fname = name if name else f.__name__

    required = get_required_params(typed_signature)

    parameters = get_parameters(required, param_annotations)

    function = Function(
        description=description,
        name=fname,
        parameters=parameters,
    )

    return model_dump(function)
