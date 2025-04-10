import asyncio
import functools
import warnings
from textwrap import dedent
from typing import Any, Callable, Sequence, List

from pydantic import BaseModel
from typing_extensions import Self

from . import SummarizngFunction

from ...models import LLMMessage
from ..._component_config import Component
from ..._function_utils import (
    args_base_model_from_signature,
    get_typed_signature,
)
from ...code_executor._func_with_reqs import Import, import_to_str, to_code
from ...tools._base import BaseTool


class SummaryFunctionConfig(BaseModel):
    """Configuration for a function tool."""
    source_code: str
    name: str
    global_imports: Sequence[Import]


class SummaryFunction(BaseTool[BaseModel, BaseModel], Component[SummaryFunctionConfig]):
    component_provider_override = "autogen_core.model_context.conditions.SummaryFunction"
    component_config_schema = SummaryFunctionConfig

    def __init__(
        self,
        func: SummarizngFunction,
        name: str | None = None,
        global_imports: Sequence[Import] = [],
        strict: bool = False,
    ) -> None:
        self._func = func
        self._global_imports = global_imports
        self._signature = get_typed_signature(func)
        func_name = name or func.func.__name__ if isinstance(func, functools.partial) else name or func.__name__
        args_model = args_base_model_from_signature(func_name + "args", self._signature)
        return_type = self._signature.return_annotation
        super().__init__(args_model, return_type, func_name, "", strict)

    def run(self, messages: List[LLMMessage], non_summary_messages: List[LLMMessage]) -> Any:
        result = self._func(messages, non_summary_messages)
        return result

    def _to_config(self) -> SummaryFunctionConfig:
        return SummaryFunctionConfig(
            source_code=dedent(to_code(self._func)),
            global_imports=self._global_imports,
            name=self.name,
        )

    @classmethod
    def _from_config(cls, config: SummaryFunctionConfig) -> Self:
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
        func: SummarizngFunction = exec_globals[func_name]
        if not callable(func):
            raise TypeError(f"Expected function but got {type(func)}")

        return cls(func)