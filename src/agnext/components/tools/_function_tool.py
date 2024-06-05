import asyncio
import functools
from typing import Any, Callable

from pydantic import BaseModel

from ...core import CancellationToken
from .._function_utils import (
    args_base_model_from_signature,
    get_typed_signature,
    return_value_base_model_from_signature,
)
from ._base import BaseTool


class FunctionTool(BaseTool[BaseModel, BaseModel]):
    def __init__(self, func: Callable[..., Any], description: str, name: str | None = None) -> None:
        self._func = func
        signature = get_typed_signature(func)
        func_name = name or func.__name__
        args_model = args_base_model_from_signature(func_name + "args", signature)
        return_model = return_value_base_model_from_signature(func_name + "return", signature)
        self._has_cancellation_support = "cancellation_token" in signature.parameters

        super().__init__(args_model, return_model, func_name, description)

    async def run(self, args: BaseModel, cancellation_token: CancellationToken) -> BaseModel:
        if asyncio.iscoroutinefunction(self._func):
            if self._has_cancellation_support:
                result = await self._func(**args.model_dump(), cancellation_token=cancellation_token)
            else:
                result = await self._func(**args.model_dump())
        else:
            if self._has_cancellation_support:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, functools.partial(self._func, **args.model_dump(), cancellation_token=cancellation_token)
                )
            else:
                future = asyncio.get_event_loop().run_in_executor(
                    None, functools.partial(self._func, **args.model_dump())
                )
                cancellation_token.link_future(future)
                result = await future

        assert isinstance(result, BaseModel)
        return result
