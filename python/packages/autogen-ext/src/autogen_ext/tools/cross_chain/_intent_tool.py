
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
import httpx
from autogen_core import CancellationToken, Component
from autogen_core.tools import BaseTool

class CrossChainOrder(BaseModel):
    swapper: str = Field(..., description="The address of the swapper")
    nonce: int = Field(..., description="A unique nonce for the order")
    originChainId: int = Field(..., description="The ID of the origin chain")
    expiry: int = Field(..., description="The expiration timestamp of the order")
    staticOutput: str = Field(..., description="The address of the static output")
    fillDeadline: int = Field(..., description="The deadline for filling the order")
    orderData: str = Field(..., description="Additional order data (hex string or encoded bytes)")

class CrossChainIntentResponse(BaseModel):
    intent_id: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None
    status_code: Optional[int] = None

class CrossChainIntentToolConfig(BaseModel):
    solver_url: str
    name: str = "cross_chain_intent"
    description: str = "Submit a cross-chain intent to a solver following ERC-7683 standard."

class CrossChainIntentTool(BaseTool[CrossChainOrder, CrossChainIntentResponse], Component[CrossChainIntentToolConfig]):
    """A tool for submitting cross-chain intents following ERC-7683 standards.

    This tool allows agents to formulate and submit cross-chain swap or bridge intents
    to a solver or an intent engine.
    """

    component_type = "tool"
    component_provider_override = "autogen_ext.tools.cross_chain.CrossChainIntentTool"
    component_config_schema = CrossChainIntentToolConfig

    def __init__(
        self,
        solver_url: str,
        name: str = "cross_chain_intent",
        description: str = "Submit a cross-chain intent to a solver following ERC-7683 standard.",
    ) -> None:
        super().__init__(CrossChainOrder, CrossChainIntentResponse, name, description)
        self._solver_url = solver_url

    async def run(self, args: CrossChainOrder, cancellation_token: CancellationToken) -> CrossChainIntentResponse:
        """Submit the cross-chain order to the solver."""
        order_dict = args.model_dump()

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self._solver_url,
                    json=order_dict,
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                # Handle potential camelCase from API
                intent_id = data.get("intentId") or data.get("intent_id")
                return CrossChainIntentResponse(intent_id=intent_id, status=data.get("status"))
            except httpx.HTTPStatusError as e:
                return CrossChainIntentResponse(error=f"HTTP error occurred: {e}", status_code=e.response.status_code)
            except Exception as e:
                return CrossChainIntentResponse(error=f"An error occurred: {str(e)}")

    def _to_config(self) -> CrossChainIntentToolConfig:
        return CrossChainIntentToolConfig(
            solver_url=self._solver_url,
            name=self.name,
            description=self.description
        )

    @classmethod
    def _from_config(cls, config: CrossChainIntentToolConfig) -> "CrossChainIntentTool":
        return cls(
            solver_url=config.solver_url,
            name=config.name,
            description=config.description
        )
