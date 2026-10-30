from typing import Any, Type
import pydantic

from ._agent_id import AgentId
from ._intervention import DefaultInterventionHandler, DropMessage

__all__ = ["JSONValidationIntervention"]


class JSONValidationIntervention(DefaultInterventionHandler):
    """
    An intervention handler that validates JSON responses against a provided Pydantic model.
    If the response looks like JSON and fails validation, it intercepts the message 
    and modifies it to prompt the agent to fix the formatting.
    """

    def __init__(self, model_type: Type[pydantic.BaseModel]):
        self._model_type = model_type
        self._type_adapter = pydantic.TypeAdapter(model_type)

    async def on_response(
        self, message: Any, *, sender: AgentId, recipient: AgentId | None
    ) -> Any | type[DropMessage]:
        
        # Check if message is a TextMessage and contains string content
        if type(message).__name__ == "TextMessage" and hasattr(message, "content") and isinstance(message.content, str):
            content = message.content.strip()
            
            # Simple heuristic to detect if the response was attempting to be JSON
            if content.startswith("{") or content.startswith("["):
                try:
                    self._type_adapter.validate_json(content)
                except pydantic.ValidationError as e:
                    # The "Healing" Part: Do not crash. Instead, modify the message 
                    # to prompt the agent with the exact error.
                    message.content = f"Your JSON was invalid because: {str(e)}. Please fix the formatting and try again."
                    if hasattr(message, "source"):
                        message.source = "system"
                        
        return message
