from __future__ import annotations

import asyncio
import inspect
from typing import TYPE_CHECKING, Any, Callable, Dict, Type, cast

from autogen_core import CancellationToken
from autogen_core.components.tools import BaseTool
from pydantic import BaseModel, Field, create_model

if TYPE_CHECKING:
    from langchain_core.tools import Tool as LangChainTool


class LangChainToolAdapter(BaseTool[BaseModel, Any]):
    """Allows you to wrap a LangChain tool and make it available to AutoGen.

    .. note::

        This class requires the :code:`langchain` extra for the :code:`autogen-ext` package.


    Args:
        langchain_tool (LangChainTool): A LangChain tool to wrap
    """

    def __init__(self, langchain_tool: LangChainTool):
        self._langchain_tool: LangChainTool = langchain_tool

        # Extract name and description
        name = self._langchain_tool.name
        description = self._langchain_tool.description or ""

        # Determine the callable method
        if hasattr(self._langchain_tool, "func") and callable(self._langchain_tool.func):
            assert self._langchain_tool.func is not None
            self._callable: Callable[..., Any] = self._langchain_tool.func
        elif hasattr(self._langchain_tool, "_run") and callable(self._langchain_tool._run):  # pyright: ignore
            self._callable: Callable[..., Any] = self._langchain_tool._run  # type: ignore
        else:
            raise AttributeError(
                f"The provided LangChain tool '{name}' does not have a callable 'func' or '_run' method."
            )

        # Determine args_type
        if self._langchain_tool.args_schema:  # pyright: ignore
            args_type = self._langchain_tool.args_schema  # pyright: ignore
        else:
            # Infer args_type from the callable's signature
            sig = inspect.signature(cast(Callable[..., Any], self._callable))  # type: ignore
            fields = {
                k: (v.annotation, Field(...))
                for k, v in sig.parameters.items()
                if k != "self" and v.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            }
            args_type = create_model(f"{name}Args", **fields)  # type: ignore
            # Note: type ignore is used due to a LangChain typing limitation

        # Ensure args_type is a subclass of BaseModel
        if not issubclass(args_type, BaseModel):
            raise ValueError(f"Failed to create a valid Pydantic v2 model for {name}")

        # Assume return_type as Any if not specified
        return_type: Type[Any] = object

        super().__init__(args_type, return_type, name, description)

    async def run(self, args: BaseModel, cancellation_token: CancellationToken) -> Any:
        # Prepare arguments
        kwargs = args.model_dump()

        # Determine if the callable is asynchronous
        if inspect.iscoroutinefunction(self._callable):
            result = await self._callable(**kwargs)
        else:
            # Run in a thread to avoid blocking the event loop
            result = await asyncio.to_thread(self._call_sync, kwargs)

        return result

    def _call_sync(self, kwargs: Dict[str, Any]) -> Any:
        return self._callable(**kwargs)
