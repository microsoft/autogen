"""Nory x402 Payment Tools for AutoGen.

Tools for AI agents to make payments using the x402 HTTP protocol.
Supports Solana and 7 EVM chains with sub-400ms settlement.
"""

from typing import Any, Literal, Optional, Type

import httpx
from autogen_core import CancellationToken, Component
from autogen_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing_extensions import Self

NORY_API_BASE = "https://noryx402.com"
DEFAULT_TIMEOUT = 30.0


class NoryNetwork(str):
    """Supported blockchain networks."""

    SOLANA_MAINNET = "solana-mainnet"
    SOLANA_DEVNET = "solana-devnet"
    BASE_MAINNET = "base-mainnet"
    POLYGON_MAINNET = "polygon-mainnet"
    ARBITRUM_MAINNET = "arbitrum-mainnet"
    OPTIMISM_MAINNET = "optimism-mainnet"
    AVALANCHE_MAINNET = "avalanche-mainnet"
    SEI_MAINNET = "sei-mainnet"
    IOTEX_MAINNET = "iotex-mainnet"


# Input schemas for tools
class PaymentRequirementsInput(BaseModel):
    """Input for getting payment requirements."""

    resource: str = Field(description="The resource path requiring payment (e.g., /api/premium/data)")
    amount: str = Field(description="Amount in human-readable format (e.g., '0.10' for $0.10 USDC)")
    network: Optional[str] = Field(default=None, description="Preferred blockchain network")


class VerifyPaymentInput(BaseModel):
    """Input for verifying a payment."""

    payload: str = Field(description="Base64-encoded payment payload containing signed transaction")


class SettlePaymentInput(BaseModel):
    """Input for settling a payment."""

    payload: str = Field(description="Base64-encoded payment payload")


class TransactionLookupInput(BaseModel):
    """Input for looking up a transaction."""

    transaction_id: str = Field(description="Transaction ID or signature")
    network: str = Field(description="Network where the transaction was submitted")


class HealthCheckInput(BaseModel):
    """Input for health check (empty)."""

    pass


# Tool configs
class NoryToolConfig(BaseModel):
    """Base configuration for Nory tools."""

    api_key: Optional[str] = Field(default=None, description="Nory API key (optional for public endpoints)")
    timeout: float = Field(default=DEFAULT_TIMEOUT, description="Request timeout in seconds")


class NoryPaymentRequirementsTool(BaseTool[PaymentRequirementsInput, dict], Component[NoryToolConfig]):
    """Get x402 payment requirements for accessing a paid resource.

    Use this when you encounter an HTTP 402 Payment Required response
    and need to know how much to pay and where to send payment.

    .. note::
        This tool is part of the Nory x402 payment integration.

    Example:
        Get payment requirements for a resource::

            from autogen_ext.tools.nory import NoryPaymentRequirementsTool

            tool = NoryPaymentRequirementsTool()
            result = await tool.run(
                PaymentRequirementsInput(
                    resource="/api/premium/data",
                    amount="0.10",
                    network="solana-mainnet"
                ),
                CancellationToken()
            )
    """

    component_type = "tool"
    component_provider_override = "autogen_ext.tools.nory.NoryPaymentRequirementsTool"
    component_config_schema = NoryToolConfig

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._config = NoryToolConfig(api_key=api_key, timeout=timeout)
        super().__init__(
            PaymentRequirementsInput,
            dict,
            "nory_get_payment_requirements",
            "Get x402 payment requirements for a resource. Returns amount, supported networks, and wallet address.",
        )

    def _to_config(self) -> NoryToolConfig:
        return self._config.model_copy()

    @classmethod
    def _from_config(cls, config: NoryToolConfig) -> Self:
        return cls(**config.model_dump())

    async def run(self, args: PaymentRequirementsInput, cancellation_token: CancellationToken) -> dict:
        params = {"resource": args.resource, "amount": args.amount}
        if args.network:
            params["network"] = args.network

        headers = {}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"

        timeout = httpx.Timeout(timeout=self._config.timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                f"{NORY_API_BASE}/api/x402/requirements",
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()


class NoryVerifyPaymentTool(BaseTool[VerifyPaymentInput, dict], Component[NoryToolConfig]):
    """Verify a signed payment transaction before settlement.

    Use this to validate that a payment transaction is correct
    before submitting it to the blockchain.
    """

    component_type = "tool"
    component_provider_override = "autogen_ext.tools.nory.NoryVerifyPaymentTool"
    component_config_schema = NoryToolConfig

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._config = NoryToolConfig(api_key=api_key, timeout=timeout)
        super().__init__(
            VerifyPaymentInput,
            dict,
            "nory_verify_payment",
            "Verify a signed payment transaction before submitting to blockchain.",
        )

    def _to_config(self) -> NoryToolConfig:
        return self._config.model_copy()

    @classmethod
    def _from_config(cls, config: NoryToolConfig) -> Self:
        return cls(**config.model_dump())

    async def run(self, args: VerifyPaymentInput, cancellation_token: CancellationToken) -> dict:
        headers = {"Content-Type": "application/json"}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"

        timeout = httpx.Timeout(timeout=self._config.timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{NORY_API_BASE}/api/x402/verify",
                json={"payload": args.payload},
                headers=headers,
            )
            response.raise_for_status()
            return response.json()


class NorySettlePaymentTool(BaseTool[SettlePaymentInput, dict], Component[NoryToolConfig]):
    """Settle a payment on-chain.

    Use this to submit a verified payment transaction to the blockchain.
    Settlement typically completes in under 400ms.
    """

    component_type = "tool"
    component_provider_override = "autogen_ext.tools.nory.NorySettlePaymentTool"
    component_config_schema = NoryToolConfig

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._config = NoryToolConfig(api_key=api_key, timeout=timeout)
        super().__init__(
            SettlePaymentInput,
            dict,
            "nory_settle_payment",
            "Submit a verified payment to the blockchain for settlement (~400ms).",
        )

    def _to_config(self) -> NoryToolConfig:
        return self._config.model_copy()

    @classmethod
    def _from_config(cls, config: NoryToolConfig) -> Self:
        return cls(**config.model_dump())

    async def run(self, args: SettlePaymentInput, cancellation_token: CancellationToken) -> dict:
        headers = {"Content-Type": "application/json"}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"

        timeout = httpx.Timeout(timeout=self._config.timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{NORY_API_BASE}/api/x402/settle",
                json={"payload": args.payload},
                headers=headers,
            )
            response.raise_for_status()
            return response.json()


class NoryTransactionLookupTool(BaseTool[TransactionLookupInput, dict], Component[NoryToolConfig]):
    """Look up transaction status.

    Use this to check the status of a previously submitted payment.
    """

    component_type = "tool"
    component_provider_override = "autogen_ext.tools.nory.NoryTransactionLookupTool"
    component_config_schema = NoryToolConfig

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._config = NoryToolConfig(api_key=api_key, timeout=timeout)
        super().__init__(
            TransactionLookupInput,
            dict,
            "nory_transaction_lookup",
            "Look up the status and details of a transaction.",
        )

    def _to_config(self) -> NoryToolConfig:
        return self._config.model_copy()

    @classmethod
    def _from_config(cls, config: NoryToolConfig) -> Self:
        return cls(**config.model_dump())

    async def run(self, args: TransactionLookupInput, cancellation_token: CancellationToken) -> dict:
        headers = {}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"

        timeout = httpx.Timeout(timeout=self._config.timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(
                f"{NORY_API_BASE}/api/x402/transactions/{args.transaction_id}",
                params={"network": args.network},
                headers=headers,
            )
            response.raise_for_status()
            return response.json()


class NoryHealthCheckTool(BaseTool[HealthCheckInput, dict], Component[NoryToolConfig]):
    """Check Nory service health.

    Use this to verify the payment service is operational
    and see supported networks.
    """

    component_type = "tool"
    component_provider_override = "autogen_ext.tools.nory.NoryHealthCheckTool"
    component_config_schema = NoryToolConfig

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._config = NoryToolConfig(api_key=api_key, timeout=timeout)
        super().__init__(
            HealthCheckInput,
            dict,
            "nory_health_check",
            "Check health status of Nory x402 payment service.",
        )

    def _to_config(self) -> NoryToolConfig:
        return self._config.model_copy()

    @classmethod
    def _from_config(cls, config: NoryToolConfig) -> Self:
        return cls(**config.model_dump())

    async def run(self, args: HealthCheckInput, cancellation_token: CancellationToken) -> dict:
        timeout = httpx.Timeout(timeout=self._config.timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{NORY_API_BASE}/api/x402/health")
            response.raise_for_status()
            return response.json()
