import asyncio
import functools
import warnings
from textwrap import dedent
from typing import Any, Callable, Sequence

from pydantic import BaseModel
from typing_extensions import Self

from .. import CancellationToken
from .._component_config import Component
from .._function_utils import (
    args_base_model_from_signature,
    get_typed_signature,
)
from ..code_executor._func_with_reqs import Import, import_to_str, to_code
from ._base import BaseTool


class FunctionToolConfig(BaseModel):
    """Configuration for a function tool."""

    source_code: str
    name: str
    description: str
    global_imports: Sequence[Import]
    has_cancellation_support: bool


class FunctionTool(BaseTool[BaseModel, BaseModel], Component[FunctionToolConfig]):
    """
    Create custom tools by wrapping standard Python functions.

    `FunctionTool` offers an interface for executing Python functions either asynchronously or synchronously.
    Each function must include type annotations for all parameters and its return type. These annotations
    enable `FunctionTool` to generate a schema necessary for input validation, serialization, and for informing
    the LLM about expected parameters. When the LLM prepares a function call, it leverages this schema to
    generate arguments that align with the function's specifications.

    .. note::

        It is the user's responsibility to verify that the tool's output type matches the expected type.

    Args:
        func (Callable[..., ReturnT | Awaitable[ReturnT]]): The function to wrap and expose as a tool.
        description (str): A description to inform the model of the function's purpose, specifying what
            it does and the context in which it should be called.
        name (str, optional): An optional custom name for the tool. Defaults to
            the function's original name if not provided.

    Example:

        .. code-block:: python

            import random
            from autogen_core import CancellationToken
            from autogen_core.tools import FunctionTool
            from typing_extensions import Annotated
            import asyncio


            async def get_stock_price(ticker: str, date: Annotated[str, "Date in YYYY/MM/DD"]) -> float:
                # Simulates a stock price retrieval by returning a random float within a specified range.
                return random.uniform(10, 200)


            async def example():
                # Initialize a FunctionTool instance for retrieving stock prices.
                stock_price_tool = FunctionTool(get_stock_price, description="Fetch the stock price for a given ticker.")

                # Execute the tool with cancellation support.
                cancellation_token = CancellationToken()
                result = await stock_price_tool.run_json({"ticker": "AAPL", "date": "2021/01/01"}, cancellation_token)

                # Output the result as a formatted string.
                print(stock_price_tool.return_value_as_string(result))


            asyncio.run(example())
    """

    component_provider_override = "autogen_core.tools.FunctionTool"
    component_config_schema = FunctionToolConfig

    def __init__(
        self, func: Callable[..., Any], description: str, name: str | None = None, global_imports: Sequence[Import] = []
    ) -> None:
        self._func = func
        self._global_imports = global_imports
        signature = get_typed_signature(func)
        func_name = name or func.func.__name__ if isinstance(func, functools.partial) else name or func.__name__
        args_model = args_base_model_from_signature(func_name + "args", signature)
        return_type = signature.return_annotation
        self._has_cancellation_support = "cancellation_token" in signature.parameters

        super().__init__(args_model, return_type, func_name, description)

    async def run(self, args: BaseModel, cancellation_token: CancellationToken) -> Any:
        if asyncio.iscoroutinefunction(self._func):
            if self._has_cancellation_support:
                result = await self._func(**args.model_dump(), cancellation_token=cancellation_token)
            else:
                result = await self._func(**args.model_dump())
        else:
            if self._has_cancellation_support:
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    functools.partial(
                        self._func,
                        **args.model_dump(),
                        cancellation_token=cancellation_token,
                    ),
                )
            else:
                future = asyncio.get_event_loop().run_in_executor(
                    None, functools.partial(self._func, **args.model_dump())
                )
                cancellation_token.link_future(future)
                result = await future

        return result

    def _to_config(self) -> FunctionToolConfig:
        return FunctionToolConfig(
            source_code=dedent(to_code(self._func)),
            global_imports=self._global_imports,
            name=self.name,
            description=self.description,
            has_cancellation_support=self._has_cancellation_support,
        )

    @classmethod
    def _from_config(cls, config: FunctionToolConfig) -> Self:
        warnings.warn(
            "\n⚠️  SECURITY WARNING ⚠️\n"
            "Loading a FunctionTool from config will execute code to import the provided global imports and and function code.\n"
            "Only load configs from TRUSTED sources to prevent arbitrary code execution.",
            UserWarning,
            stacklevel=2,
        )

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

        return cls(func, "", None)
