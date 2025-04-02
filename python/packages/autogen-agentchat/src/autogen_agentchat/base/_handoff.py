import logging
from typing import Any, Dict

from autogen_core.tools import BaseTool, FunctionTool
from pydantic import BaseModel, Field, model_validator

from .. import EVENT_LOGGER_NAME

event_logger = logging.getLogger(EVENT_LOGGER_NAME)


class Handoff(BaseModel):
    """Handoff configuration."""

    target: str
    """The name of the target agent to handoff to."""

    description: str = Field(default="")
    """The description of the handoff such as the condition under which it should happen and the target agent's ability.
    If not provided, it is generated from the target agent's name."""

    name: str = Field(default="")
    """The name of this handoff configuration. If not provided, it is generated from the target agent's name."""

    message: str = Field(default="")
    """The message to the target agent.
    By default, it will be the result for the handoff tool.
    If not provided, it is generated from the target agent's name."""

    @model_validator(mode="before")
    @classmethod
    def set_defaults(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not values.get("description"):
            values["description"] = f"Handoff to {values['target']}."
        if not values.get("name"):
            values["name"] = f"transfer_to_{values['target']}".lower()
        else:
            name = values["name"]
            if not isinstance(name, str):
                raise ValueError(f"Handoff name must be a string: {values['name']}")
            # Check if name is a valid identifier.
            if not name.isidentifier():
                raise ValueError(f"Handoff name must be a valid identifier: {values['name']}")
        if not values.get("message"):
            values["message"] = (
                f"Transferred to {values['target']}, adopting the role of {values['target']} immediately."
            )
        return values

    @property
    def handoff_tool(self) -> BaseTool[BaseModel, BaseModel]:
        """Create a handoff tool from this handoff configuration."""

        def _handoff_tool() -> str:
            return self.message

        return FunctionTool(_handoff_tool, name=self.name, description=self.description, strict=True)

    """
    The tool that can be used to handoff to the target agent.
    Typically, the results of the tool's execution are provided to the target agent.
    """
