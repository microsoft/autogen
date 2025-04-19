from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any, List, Literal, Mapping, Optional, Type

from pydantic import BaseModel, Field
from typing_extensions import Annotated, Self

from .._component_config import ComponentBase
from .._image import Image
from ._base import ToolSchema


class TextResultContent(BaseModel):
    """
    Text result content of a tool execution.
    """

    type: Literal["TextResultContent"] = "TextResultContent"
    content: str


class ImageResultContent(BaseModel):
    """
    Image result content of a tool execution.
    """

    type: Literal["ImageResultContent"] = "ImageResultContent"
    content: Image


ResultContent = Annotated[TextResultContent | ImageResultContent, Field(discriminator="type")]


class ToolResult(BaseModel):
    """
    A result of a tool execution.

    Attributes:
        name: The name of the tool that was executed.
        result: The result of the tool execution.
        is_error: Whether the tool execution resulted in an error.
    """

    type: Literal["ToolResult"] = "ToolResult"
    name: str
    result: List[ResultContent]
    is_error: bool = False


class WorkBench(ABC, ComponentBase[BaseModel]):
    """
    A workbench is a component that provides a set of tools that may share
    resources and state.

    The workbench is responsible for managing the lifecycle of the tools and
    providing a single interface to call them. The tools provided by the workbench
    may be dynamic and their availabilities may change after each tool execution.
    """

    @abstractmethod
    async def list_tools(self) -> List[ToolSchema]:
        """
        List the currently available tools in the workbench as :class:`ToolSchema`
        objects.

        The list of tools may be dynamic, and their content may change after
        tool execution.
        """
        ...

    @abstractmethod
    async def call_tool(self, name: str, arguments: Mapping[str, Any] | None = None) -> ToolResult:
        """
        Call a tool in the workbench.

        Args:
            name (str): The name of the tool to call.
            arguments (Mapping[str, Any] | None): The arguments to pass to the tool.
                If None, the tool will be called with no arguments.
        Returns:
            ToolResult: The result of the tool execution.
        """
        ...

    @abstractmethod
    async def start(self) -> None:
        """
        Start the workbench and initialize any resources.

        This method should be called before using the workbench.
        """
        ...

    @abstractmethod
    async def stop(self) -> None:
        """
        Stop the workbench and release any resources.

        This method should be called when the workbench is no longer needed.
        """
        ...

    @abstractmethod
    async def reset(self) -> None:
        """
        Reset the workbench to its initialized, started state.
        """
        ...

    @abstractmethod
    async def save_state(self) -> Mapping[str, Any]:
        """
        Save the state of the workbench.

        This method should be called to persist the state of the workbench.
        """
        ...

    @abstractmethod
    async def load_state(self, state: Mapping[str, Any]) -> None:
        """
        Load the state of the workbench.

        Args:
            state (Mapping[str, Any]): The state to load into the workbench.
        """
        ...

    async def __aenter__(self) -> Self:
        """
        Enter the workbench context manager.

        This method is called when the workbench is used in a `with` statement.
        It calls the :meth:`~autogen_core.tools.WorkBench.start` method to start the workbench.
        """
        await self.start()
        return self

    async def __aexit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        """
        Exit the workbench context manager.
        This method is called when the workbench is used in a `with` statement.
        It calls the :meth:`~autogen_core.tools.WorkBench.stop` method to stop the workbench.
        """
        await self.stop()
