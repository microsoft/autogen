from __future__ import annotations

from functools import partial
from typing import Annotated

import pytest
from autogen_core import CancellationToken
from autogen_core._function_utils import get_typed_signature
from autogen_core.tools import FunctionTool
from pydantic import BaseModel


class Payload(BaseModel):
    value: str


def describe(prefix: str, payload: Annotated[Payload, "The payload"]) -> Payload:
    return Payload(value=prefix + payload.value)


@pytest.mark.parametrize("bind_keyword", [False, True])
@pytest.mark.asyncio
async def test_partial_tool_resolves_postponed_annotations(bind_keyword: bool) -> None:
    bound = partial(describe, prefix="hello ") if bind_keyword else partial(describe, "hello ")
    signature = get_typed_signature(bound)
    assert signature.return_annotation is Payload
    assert signature.parameters["payload"].annotation == Annotated[Payload, "The payload"]
    if not bind_keyword:
        assert "prefix" not in signature.parameters
    tool = FunctionTool(bound, description="Describe the payload")
    result = await tool.run_json({"payload": {"value": "world"}}, CancellationToken())
    assert result == Payload(value="hello world")


def test_regular_function_still_resolves_annotations() -> None:
    signature = get_typed_signature(describe)
    assert signature.return_annotation is Payload
    assert signature.parameters["prefix"].annotation is str
