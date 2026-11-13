from typing import Any

from ._agent_id import AgentId
from ._intervention import DefaultInterventionHandler, DropMessage
from .utils._price_map import PriceMap


class CostInterventionHandler(DefaultInterventionHandler):
    def __init__(self) -> None:
        self._total_cost: float = 0.0

    async def on_response(
        self, message: Any, *, sender: AgentId, recipient: AgentId | None
    ) -> Any | type[DropMessage]:
        
        if hasattr(message, "models_usage") and message.models_usage:
            prompt_tokens = getattr(message.models_usage, "prompt_tokens", 0)
            completion_tokens = getattr(message.models_usage, "completion_tokens", 0)
            model = getattr(message, "model", "gpt-4o")
            
            self._total_cost += PriceMap.calculate(model, prompt_tokens, completion_tokens)
            
        return await super().on_response(message, sender=sender, recipient=recipient)
