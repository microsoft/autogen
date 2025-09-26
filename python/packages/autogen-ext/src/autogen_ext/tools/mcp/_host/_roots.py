from abc import ABC, abstractmethod
from typing import Generic, List, Sequence, TypeVar

from autogen_core import Component, ComponentBase
from pydantic import BaseModel

from mcp import types as mcp_types


class RootsProvider(ABC, ComponentBase[BaseModel]):
    """A serializable base class for handling callable roots listing."""

    component_type = "mcp_roots_provider"

    @abstractmethod
    async def list_roots(self) -> mcp_types.ListRootsResult | mcp_types.ErrorData:
        """List the available roots."""
        ...


class StaticRootsProviderConfig(BaseModel):
    roots: List[mcp_types.Root]


class StaticRootsProvider(RootsProvider, Component[StaticRootsProviderConfig]):
    component_config_schema = StaticRootsProviderConfig
    component_provider_override = "autogen_ext.tools.mcp.StaticRootsProvider"

    def __init__(self, roots: Sequence[mcp_types.Root]):
        self._roots = list(roots)

    async def list_roots(self) -> mcp_types.ListRootsResult:
        # Return a copy so callers can't mutate our internal list.
        return mcp_types.ListRootsResult(roots=list(self._roots))

    def _to_config(self) -> BaseModel:
        return StaticRootsProviderConfig(roots=self._roots)

    @classmethod
    def _from_config(cls, config: StaticRootsProviderConfig):
        return StaticRootsProvider(roots=config.roots)
