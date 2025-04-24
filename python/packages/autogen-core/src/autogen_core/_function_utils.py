# File based from: https://github.com/microsoft/autogen/blob/47f905267245e143562abfb41fcba503a9e1d56d/autogen/function_utils.py
# Credit to original authors

import ast
import inspect
import textwrap
import typing
from functools import partial
from logging import getLogger
from typing import (
    Annotated,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
)

from pydantic import BaseModel, Field, TypeAdapter, create_model  # type: ignore
from pydantic_core import PydanticUndefined
from typing_extensions import Literal
from .code_executor import Import, Alias, ImportFromModule

logger = getLogger(__name__)

T = TypeVar("T")


def get_typed_signature(call: Callable[..., Any]) -> inspect.Signature:
    """Get the signature of a function with type annotations.

    Args:
        call: The function to get the signature for

    Returns:
        The signature of the function with type annotations
    """
    signature = inspect.signature(call)
    globalns = getattr(call, "__globals__", {})
    func_call = call.func if isinstance(call, partial) else call
    type_hints = typing.get_type_hints(func_call, globalns, include_extras=True)
    typed_params = [
        inspect.Parameter(
            name=param.name,
            kind=param.kind,
            default=param.default,
            annotation=type_hints[param.name],
        )
        for param in signature.parameters.values()
    ]
    return_annotation = type_hints.get("return", inspect.Signature.empty)
    typed_signature = inspect.Signature(typed_params, return_annotation=return_annotation)
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
    type_hints = typing.get_type_hints(call, globalns, include_extras=True)
    return type_hints.get("return", inspect.Signature.empty)


def get_param_annotations(
    typed_signature: inspect.Signature,
) -> Dict[str, Union[Annotated[Type[Any], str], Type[Any]]]:
    """Get the type annotations of the parameters of a function

    Args:
        typed_signature: The signature of the function with type annotations

    Returns:
        A dictionary of the type annotations of the parameters of the function
    """
    return {
        k: v.annotation for k, v in typed_signature.parameters.items() if v.annotation is not inspect.Signature.empty
    }


class Parameters(BaseModel):
    """Parameters of a function as defined by the OpenAI API"""

    type: Literal["object"] = "object"
    properties: Dict[str, Dict[str, Any]]
    required: List[str]


class Function(BaseModel):
    """A function as defined by the OpenAI API"""

    description: Annotated[str, Field(description="Description of the function")]
    name: Annotated[str, Field(description="Name of the function")]
    parameters: Annotated[Parameters, Field(description="Parameters of the function")]


class ToolFunction(BaseModel):
    """A function under tool as defined by the OpenAI API."""

    type: Literal["function"] = "function"
    function: Annotated[Function, Field(description="Function under tool")]


def type2description(k: str, v: Union[Annotated[Type[Any], str], Type[Any]]) -> str:
    # handles Annotated
    if hasattr(v, "__metadata__"):
        retval = v.__metadata__[0]
        if isinstance(retval, str):
            return retval
        else:
            raise ValueError(f"Invalid description {retval} for parameter {k}, should be a string.")
    else:
        return k


def get_parameter_json_schema(k: str, v: Any, default_values: Dict[str, Any]) -> Dict[str, Any]:
    """Get a JSON schema for a parameter as defined by the OpenAI API

    Args:
        k: The name of the parameter
        v: The type of the parameter
        default_values: The default values of the parameters of the function

    Returns:
        A Pydanitc model for the parameter
    """

    schema = TypeAdapter(v).json_schema()
    if k in default_values:
        dv = default_values[k]
        schema["default"] = dv

    schema["description"] = type2description(k, v)

    return schema


def get_required_params(typed_signature: inspect.Signature) -> List[str]:
    """Get the required parameters of a function

    Args:
        typed_signature: The signature of the function as returned by inspect.signature

    Returns:
        A list of the required parameters of the function
    """
    return [k for k, v in typed_signature.parameters.items() if v.default == inspect.Signature.empty]


def get_default_values(typed_signature: inspect.Signature) -> Dict[str, Any]:
    """Get default values of parameters of a function

    Args:
        typed_signature: The signature of the function as returned by inspect.signature

    Returns:
        A dictionary of the default values of the parameters of the function
    """
    return {k: v.default for k, v in typed_signature.parameters.items() if v.default != inspect.Signature.empty}


def get_parameters(
    required: List[str],
    param_annotations: Dict[str, Union[Annotated[Type[Any], str], Type[Any]]],
    default_values: Dict[str, Any],
) -> Parameters:
    """Get the parameters of a function as defined by the OpenAI API

    Args:
        required: The required parameters of the function
        param_annotations: A dictionary of the type annotations of the parameters of the function
        default_values: The default values of the parameters of the function

    Returns:
        A Pydantic model for the parameters of the function
    """
    return Parameters(
        properties={
            k: get_parameter_json_schema(k, v, default_values)
            for k, v in param_annotations.items()
            if v is not inspect.Signature.empty
        },
        required=required,
    )


def get_missing_annotations(typed_signature: inspect.Signature, required: List[str]) -> Tuple[Set[str], Set[str]]:
    """Get the missing annotations of a function

    Ignores the parameters with default values as they are not required to be annotated, but logs a warning.
    Args:
        typed_signature: The signature of the function with type annotations
        required: The required parameters of the function

    Returns:
        A set of the missing annotations of the function
    """
    all_missing = {k for k, v in typed_signature.parameters.items() if v.annotation is inspect.Signature.empty}
    missing = all_missing.intersection(set(required))
    unannotated_with_default = all_missing.difference(missing)
    return missing, unannotated_with_default


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

        .. code-block:: python

            def f(
                a: Annotated[str, "Parameter a"],
                b: int = 2,
                c: Annotated[float, "Parameter c"] = 0.1,
            ) -> None:
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

    """
    typed_signature = get_typed_signature(f)
    required = get_required_params(typed_signature)
    default_values = get_default_values(typed_signature)
    param_annotations = get_param_annotations(typed_signature)
    return_annotation = get_typed_return_annotation(f)
    missing, unannotated_with_default = get_missing_annotations(typed_signature, required)

    if return_annotation is None:
        logger.warning(
            f"The return type of the function '{f.__name__}' is not annotated. Although annotating it is "
            + "optional, the function should return either a string, a subclass of 'pydantic.BaseModel'."
        )

    if unannotated_with_default != set():
        unannotated_with_default_s = [f"'{k}'" for k in sorted(unannotated_with_default)]
        logger.warning(
            f"The following parameters of the function '{f.__name__}' with default values are not annotated: "
            + f"{', '.join(unannotated_with_default_s)}."
        )

    if missing != set():
        missing_s = [f"'{k}'" for k in sorted(missing)]
        raise TypeError(
            f"All parameters of the function '{f.__name__}' without default values must be annotated. "
            + f"The annotations are missing for the following parameters: {', '.join(missing_s)}"
        )

    fname = name if name else f.__name__

    parameters = get_parameters(required, param_annotations, default_values=default_values)

    function = ToolFunction(
        function=Function(
            description=description,
            name=fname,
            parameters=parameters,
        )
    )

    return function.model_dump()


def normalize_annotated_type(type_hint: Type[Any]) -> Type[Any]:
    """Normalize typing.Annotated types to the inner type."""
    if get_origin(type_hint) is Annotated:
        # Extract the inner type from Annotated
        return get_args(type_hint)[0]  # type: ignore
    return type_hint


def args_base_model_from_signature(name: str, sig: inspect.Signature) -> Type[BaseModel]:
    fields: Dict[str, tuple[Type[Any], Any]] = {}
    for param_name, param in sig.parameters.items():
        # This is handled externally
        if param_name == "cancellation_token":
            continue

        if param.annotation is inspect.Parameter.empty:
            raise ValueError("No annotation")

        type = normalize_annotated_type(param.annotation)
        description = type2description(param_name, param.annotation)
        default_value = param.default if param.default is not inspect.Parameter.empty else PydanticUndefined

        fields[param_name] = (type, Field(default=default_value, description=description))

    return cast(BaseModel, create_model(name, **fields))  # type: ignore


class AnyCallable(Protocol):
    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...

def get_imports_from_func(func: AnyCallable) -> list[Import]:
    """Extract global imports actually used by a function.
    
    Args:
        func: The function to analyze
        
    Returns:
        List of imported modules that are actually used within the function body
    """
    # Get the source code of the module and function
    module = inspect.getmodule(func)
    if module is None:
        return []
    module_source = inspect.getsource(module)
    
    # Get function source and dedent it
    func_source = inspect.getsource(func)
    func_source = textwrap.dedent(func_source)
    
    # Parse the source code into ASTs
    module_ast = ast.parse(module_source)
    func_ast = ast.parse(func_source)
    
    # Find the function definition node in the parsed tree
    function_def = None
    for node in ast.walk(func_ast):
        if isinstance(node, ast.FunctionDef) and hasattr(func, "__name__") and node.name == func.__name__:
            function_def = node
            break
    
    if not function_def:
        return []
    
    # Collect names used within the function
    used_names: set[ast.FunctionDef] = set()
    
    class NameVisitor(ast.NodeVisitor):
        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load):
                used_names.add(node.id)
            self.generic_visit(node)
        
        def visit_Attribute(self, node):
            # Check for module.attribute pattern
            if isinstance(node.value, ast.Name):
                used_names.add(node.value.id)
            self.generic_visit(node)
    
    name_visitor = NameVisitor()
    for node in function_def.body:
        name_visitor.visit(node)

    # Visit function argument annotations
    for arg in function_def.args.args:
        if arg.annotation:
            name_visitor.visit(arg.annotation)
    
    # Visit function return type annotation
    if function_def.returns:
        name_visitor.visit(function_def.returns)
    
    # Extract all import statements from the module - including nested blocks
    all_imports = {}  # Map from alias to original module
    from_imports = {}  # Map from alias to (module, imported_name)
    
    class ImportVisitor(ast.NodeVisitor):
        def visit_Import(self, node):
            for name in node.names:
                if name.asname:
                    all_imports[name.asname] = name.name
                else:
                    all_imports[name.name] = name.name
            self.generic_visit(node)
        
        def visit_ImportFrom(self, node):
            for name in node.names:
                if name.asname:
                    from_imports[name.asname] = (node.module, name.name)
                else:
                    from_imports[name.name] = (node.module, name.name)
            self.generic_visit(node)
    
    # Visit all nodes to find imports everywhere in the module
    import_visitor = ImportVisitor()
    import_visitor.visit(module_ast)
    
    # Filter imports that are actually used in the function
    result: list[Import] = []
    
    # Check regular imports
    for used_name in used_names:
        if used_name in all_imports:
            if all_imports[used_name] == used_name:
                # Regular import (import X)
                result.append(used_name)
            else:
                # Aliased import (import X as Y)
                result.append(Alias(name=all_imports[used_name], alias=used_name))
    
    # Process from-imports
    from_modules: dict[str, list[str]] = {}
    
    for used_name in used_names:
        if used_name in from_imports:
            module, name = from_imports[used_name] # type: ignore
            if module not in from_modules:
                from_modules[module] = []
            
            if name == used_name:
                # Regular from-import (from X import Y)
                from_modules[module].append(name)
            else:
                # Aliased from-import (from X import Y as Z)
                from_modules[module].append(Alias(name=name, alias=used_name)) # type: ignore
    
    # Add from-imports to result
    for module, imports in from_modules.items():
        if imports:  # Only add if there are actually used imports
            result.append(ImportFromModule(module=module, imports=imports))
    
    return result
