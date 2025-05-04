import asyncio
import functools
import warnings
from typing import Any, Callable, Mapping, Protocol, Sequence, Type, TypeVar, runtime_checkable

from pydantic import BaseModel
from typing_extensions import Self, NotRequired, TypedDict

from ._component_config import Component, ComponentBase
from ._function_utils import (
    args_base_model_from_signature,
    get_typed_signature,
    normalize_annotated_type,
    get_imports_from_func,
)
from .code_executor._func_with_reqs import Import, import_to_str, to_code
from textwrap import dedent

T = TypeVar("T", bound=BaseModel, contravariant=True)
ReturnT = TypeVar("ReturnT", covariant=True)


class IndividualFunctionSchema(TypedDict):
    name: str
    description: NotRequired[str]
    parameters: NotRequired[dict[str, Any]]
    global_imports: Sequence[Import]
    strict: NotRequired[bool]


@runtime_checkable
class IndividualFunctionProtocol(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def schema(self) -> IndividualFunctionSchema: ...

    def args_type(self) -> Type[BaseModel]: ...

    def return_type(self) -> Type[Any]: ...

    async def run_json(self, args: Mapping[str, Any]) -> Any: ...


class IndividualFunctionConfig(BaseModel):
    """Configuration for an individual function."""
    
    source_code: str
    name: str
    description: str
    global_imports: Sequence[Import] = []


class IndividualFunction(ComponentBase[BaseModel], IndividualFunctionProtocol, Component[IndividualFunctionConfig]):
    """
    Create an individual function wrapper for execution.
    
    `IndividualFunction` provides an interface to execute a Python function with proper type handling.
    Functions must have type annotations for all parameters and return types, which are used to generate
    schemas for validation and serialization.
    
    Args:
        func (Callable[..., ReturnT]): The function to wrap
        description (str): A description explaining what the function does
        name (str, optional): Custom name for the function. Defaults to the function's name.
        strict (bool, optional): If True, enforces strict schema adherence. Defaults to False.
        
    Example:
        ```python
        async def calculate_total(amount: float, tax_rate: float) -> float:
            return amount * (1 + tax_rate)
            
        func = IndividualFunction(
            calculate_total,
            description="Calculate total amount including tax"
        )
        
        result = await func.run_json({"amount": 100.0, "tax_rate": 0.07})
        print(result)  # 107.0
        ```
    """
    
    component_type = "individual_function"
    component_provider_override = "autogen_core.IndividualFunction"
    component_config_schema = IndividualFunctionConfig
    
    def __init__(
        self,
        func: Callable[..., Any],
        description: str,
        name: str,
        global_imports: Sequence[Import] = [], 
        strict: bool = False,
    ) -> None:
        self._func = func
        self._signature = get_typed_signature(func)
        func_name = name or func.func.__name__ if isinstance(func, functools.partial) else name or func.__name__
        self._name = func_name
        self._description = description
        self._strict = strict
        self._global_imports = global_imports

        if not self._global_imports:
            self._global_imports = get_imports_from_func(self._func)
        
        # Create args model from function signature
        self._args_type = args_base_model_from_signature(func_name + "args", self._signature)
        self._return_type = normalize_annotated_type(self._signature.return_annotation)
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    @property
    def schema(self) -> IndividualFunctionSchema:
        model_schema = self._args_type.model_json_schema()
        
        parameters = {
            "type": "object",
            "properties": model_schema.get("properties", {}),
            "required": model_schema.get("required", []),
            "additionalProperties": model_schema.get("additionalProperties", False),
        }
        
        # Enforce strict mode requirements if enabled
        if self._strict:
            properties: dict[Any, Any] = parameters["properties"] # type: ignore
            if set(parameters["required"]) != set(properties.keys()):
                raise ValueError(
                    "Strict mode is enabled, but not all input arguments are marked as required. "
                    "Default arguments are not allowed in strict mode."
                )
            
            if parameters.get("additionalProperties", False):
                raise ValueError(
                    "Strict mode is enabled but additional arguments are also enabled. "
                    "This is not allowed in strict mode."
                )
        
        func_schema = IndividualFunctionSchema(
            name=self._name,
            description=self._description,
            global_imports=[import_to_str(imp) for imp in self._global_imports],
            parameters=parameters,
            strict=self._strict,
        )
        return func_schema
    
    def args_type(self) -> Type[BaseModel]:
        return self._args_type
    
    def return_type(self) -> Type[Any]:
        return self._return_type
    
    async def run(self, args: BaseModel) -> Any:
        """Execute the underlying function with given arguments."""
        kwargs = {
            key: getattr(args, key)
            for key in self._signature.parameters.keys()
            if hasattr(args, key)
        }
        
        if asyncio.iscoroutinefunction(self._func):
            result = await self._func(**kwargs)
        else:
            future = asyncio.get_event_loop().run_in_executor(
                None, 
                functools.partial(self._func, **kwargs)
            )
            result = await future
        
        return result
    
    async def run_json(self, args: Mapping[str, Any]) -> Any:
        """Execute the function with JSON-compatible arguments."""
        validated_args = self._args_type.model_validate(args)
        return await self.run(validated_args)
    
    def _to_config(self) -> IndividualFunctionConfig:
        """Convert the instance to a configuration object."""
        return IndividualFunctionConfig(
            source_code=dedent(to_code(self._func)),
            name=self.name,
            description=self.description,
            global_imports=self._global_imports,
        )
        
    @classmethod
    def _from_config(cls, config: IndividualFunctionConfig) -> Self:
        # warnings.warn(
        #     "\n⚠️  SECURITY WARNING ⚠️\n"
        #     "Loading a IndividualTool from config will execute code to import the provided global imports and and function code.\n"
        #     "Only load configs from TRUSTED sources to prevent arbitrary code execution.",
        #     UserWarning,
        #     stacklevel=2,
        # )

        exec_globals: dict[str, Any] = {}

        # Execute imports first
        for import_stmt in config.global_imports:
            import_code = import_to_str(import_stmt)
            try:
                exec(import_code, exec_globals)
            except ModuleNotFoundError as e:
                raise ModuleNotFoundError(
                    f"Failed to import {import_code}: Module not found. Please ensure the module is installed."
                ) from e
            except ImportError as e:
                raise ImportError(f"Failed to import {import_code}: {str(e)}") from e
            except Exception as e:
                raise RuntimeError(f"Unexpected error while importing {import_code}: {str(e)}") from e

        # Execute function code
        try:
            exec(config.source_code, exec_globals)
            func_name = config.source_code.split("def ")[1].split("(")[0]
        except Exception as e:
            raise ValueError(f"Could not compile and load function: {e}") from e

        # Get function and verify it's callable
        func: Callable[..., Any] = exec_globals[func_name]
        if not callable(func):
            raise TypeError(f"Expected function but got {type(func)}")

        return cls(func, "", func_name)