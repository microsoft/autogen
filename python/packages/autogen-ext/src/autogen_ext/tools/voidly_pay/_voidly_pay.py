"""VoidlyPay extension for AutoGen.

Lets an AutoGen agent call any HTTP endpoint that speaks the
[x402 protocol](https://x402.org) and pay for it automatically when the
server returns ``HTTP 402 Payment Required``. Settles in <200ms via a
Sourcify-verified USDC vault on Base mainnet
(``0xb592512932a7b354969bb48039c2dc7ad6ad1c12``).

When the optional [`voidly-pay-autogen`](https://pypi.org/project/voidly-pay-autogen/)
package is installed, the tool defers to its full toolkit
(`voidly_pay_tools()`). Otherwise it implements a self-contained x402
round-trip using the lower-level [`voidly-pay`](https://pypi.org/project/voidly-pay/)
SDK.

Sits next to ``autogen_ext.tools.http`` and ``autogen_ext.tools.mcp`` —
same shape, ``BaseTool``-based, ``Component``-loadable.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from autogen_core import CancellationToken, Component
from autogen_core.tools import BaseTool
from pydantic import BaseModel, Field
from typing_extensions import Self


class VoidlyPayArgs(BaseModel):
    """Args for VoidlyPayTool."""

    url: str = Field(
        description=(
            "HTTP URL to fetch. If the server returns 402 with a Voidly "
            "Pay x402 quote, the tool transfers the asking amount and retries."
        ),
    )
    method: str = Field(
        default="GET",
        description="HTTP method. Defaults to GET.",
    )
    body: Optional[Any] = Field(
        default=None,
        description="JSON-serialisable body for POST/PUT.",
    )
    max_amount_credits: float = Field(
        default=0.05,
        description=(
            "Cap (in Voidly credits, where 1 credit = $0.001 USDC) on a single auto-pay. Default 0.05 = $0.05."
        ),
    )


class VoidlyPayResult(BaseModel):
    """Result returned by VoidlyPayTool."""

    settled: bool = Field(
        default=False,
        description="True if the tool transferred funds and re-fetched.",
    )
    transfer_id: Optional[str] = Field(
        default=None,
        description="Voidly Pay transfer id of the settlement (if any).",
    )
    amount_micro: Optional[int] = Field(
        default=None,
        description="Amount paid in micro-USDC (1_000_000 = $1).",
    )
    recipient: Optional[str] = Field(
        default=None,
        description="DID of the endpoint operator who received the payment.",
    )
    response_status: Optional[int] = Field(
        default=None,
        description="HTTP status of the resolved response.",
    )
    response: Any = Field(
        default=None,
        description="Resolved response body (parsed JSON or text).",
    )
    blocked_by_cap: bool = Field(
        default=False,
        description="True if the tool refused to settle (price > cap).",
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message, if anything went wrong.",
    )


class VoidlyPayToolConfig(BaseModel):
    """Component config for VoidlyPayTool."""

    name: str = Field(
        default="voidly_pay_fetch",
        description="The tool name surfaced to the model.",
    )
    description: str = Field(
        default=(
            "Fetch any URL. If the server returns HTTP 402 with a Voidly "
            "Pay x402 quote, auto-transfers credits and retries."
        ),
        description="The tool description shown to the model.",
    )
    api_base: str = Field(
        default="https://api.voidly.ai",
        description="Voidly Pay API base URL.",
    )
    did: Optional[str] = Field(
        default=None,
        description=("DID of a funded wallet. Falls back to ``VOIDLY_PAY_DID`` env var, then the SDK's local keypair."),
    )
    secret_base64: Optional[str] = Field(
        default=None,
        description=(
            "base64-encoded Ed25519 secret. Falls back to ``VOIDLY_PAY_SECRET`` env var. Sensitive — never log."
        ),
    )


class VoidlyPayTool(BaseTool[VoidlyPayArgs, VoidlyPayResult], Component[VoidlyPayToolConfig]):
    """Pay-on-402 fetch via the Voidly Pay rail.

    Args:
        config (VoidlyPayToolConfig): wallet + endpoint configuration.

    Example:

        .. code-block:: python

            from autogen_ext.tools.voidly_pay import VoidlyPayTool, VoidlyPayToolConfig
            from autogen_agentchat.agents import AssistantAgent

            tool = VoidlyPayTool(VoidlyPayToolConfig())
            agent = AssistantAgent(
                name="researcher",
                model_client=...,
                tools=[tool],
            )

    Mint a DID + claim the free 10-credit faucet at
    https://voidly.ai/pay/claim, then export ``VOIDLY_PAY_DID`` +
    ``VOIDLY_PAY_SECRET``.
    """

    component_type = "tool"
    component_config_schema = VoidlyPayToolConfig
    component_provider_override = "autogen_ext.tools.voidly_pay.VoidlyPayTool"

    def __init__(self, config: Optional[VoidlyPayToolConfig] = None) -> None:
        self._config = config or VoidlyPayToolConfig()
        super().__init__(
            args_type=VoidlyPayArgs,
            return_type=VoidlyPayResult,
            name=self._config.name,
            description=self._config.description,
        )

    async def run(self, args: VoidlyPayArgs, cancellation_token: CancellationToken) -> VoidlyPayResult:
        # Prefer the maintained autogen integration when available — it
        # has a richer 402-handler with receipt verification.
        try:
            from voidly_pay_autogen import voidly_pay_tools  # type: ignore[import-not-found]

            return await self._run_via_autogen_extension(args, voidly_pay_tools)
        except ImportError:
            pass

        return await self._run_inline(args)

    async def _run_via_autogen_extension(
        self,
        args: VoidlyPayArgs,
        voidly_pay_tools_factory: Any,
    ) -> VoidlyPayResult:
        """Delegate to voidly-pay-autogen's `voidly_pay_fetch` FunctionTool."""
        client = self._build_client()
        tools = voidly_pay_tools_factory(pay=client)
        fetch_tool = next((t for t in tools if t.name == "voidly_pay_fetch"), None)
        if fetch_tool is None:
            return await self._run_inline(args)
        kwargs: dict = {
            "url": args.url,
            "method": args.method,
            "max_amount_credits": args.max_amount_credits,
        }
        if args.body is not None:
            kwargs["body"] = args.body
        raw = await fetch_tool.run_json(kwargs, CancellationToken())
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            payload = {"response": raw}
        return _to_result(payload)

    async def _run_inline(self, args: VoidlyPayArgs) -> VoidlyPayResult:
        """Self-contained x402 round-trip — independent of voidly-pay-autogen."""
        try:
            client = self._build_client()
        except ImportError as e:
            return VoidlyPayResult(error=str(e))

        try:
            import httpx
        except ImportError:
            return VoidlyPayResult(
                error=(
                    "VoidlyPayTool requires httpx. Install with: "
                    "pip install 'autogen-ext[http-tool]' or pip install httpx"
                ),
            )

        cap_micro = round(args.max_amount_credits * 1_000_000)
        async with httpx.AsyncClient(timeout=30.0) as http:
            initial = await http.request(
                args.method,
                args.url,
                json=args.body if args.body is not None else None,
            )
            if initial.status_code != 402:
                return VoidlyPayResult(
                    response_status=initial.status_code,
                    response=_safe_json(initial),
                )
            try:
                envelope = initial.json()
            except json.JSONDecodeError:
                return VoidlyPayResult(
                    response_status=initial.status_code,
                    response=initial.text[:4000],
                    error="402 envelope was not JSON",
                )
            accept = next(
                (a for a in envelope.get("accepts", []) if a.get("scheme") == "voidly-credit"),
                None,
            )
            if accept is None:
                return VoidlyPayResult(error="no voidly-credit option in 402 envelope")
            if accept["amount_micro"] > cap_micro:
                return VoidlyPayResult(
                    blocked_by_cap=True,
                    amount_micro=accept["amount_micro"],
                    recipient=accept["recipient_did"],
                )
            receipt = client.pay(
                to=accept["recipient_did"],
                amount_micro=accept["amount_micro"],
                memo=f"x402:{accept['quote_id']}",
            )
            sep = "&" if "?" in args.url else "?"
            final = await http.request(
                args.method,
                f"{args.url}{sep}quote_id={accept['quote_id']}",
                json=args.body if args.body is not None else None,
            )
            return VoidlyPayResult(
                settled=True,
                transfer_id=receipt.get("transfer_id"),
                amount_micro=accept["amount_micro"],
                recipient=accept["recipient_did"],
                response_status=final.status_code,
                response=_safe_json(final),
            )

    def _build_client(self) -> Any:
        try:
            from voidly_pay import VoidlyPay  # type: ignore[import-not-found]
        except ImportError as e:
            raise ImportError(
                "VoidlyPayTool requires the `voidly-pay` package. Install with: pip install voidly-pay"
            ) from e

        kwargs: dict = {"api_base": self._config.api_base}
        did = self._config.did or os.environ.get("VOIDLY_PAY_DID")
        secret = self._config.secret_base64 or os.environ.get("VOIDLY_PAY_SECRET")
        if did and secret:
            kwargs["did"] = did
            kwargs["secret_base64"] = secret
        return VoidlyPay(**kwargs)

    def _to_config(self) -> VoidlyPayToolConfig:
        return self._config

    @classmethod
    def _from_config(cls, config: VoidlyPayToolConfig) -> Self:
        return cls(config)


def _safe_json(response: Any) -> Any:
    """Return parsed JSON when content-type says so, else trimmed text."""
    ct = response.headers.get("content-type", "") if hasattr(response, "headers") else ""
    if ct.startswith("application/json"):
        try:
            return response.json()
        except (ValueError, TypeError):
            return response.text[:4000]
    return response.text[:4000]


def _to_result(payload: Any) -> VoidlyPayResult:
    """Coerce a dict payload from the `voidly-pay-autogen` fetch tool."""
    if not isinstance(payload, dict):
        return VoidlyPayResult(response=payload)
    return VoidlyPayResult(
        settled=bool(payload.get("settled")),
        transfer_id=payload.get("transfer_id"),
        amount_micro=payload.get("amount_micro"),
        recipient=payload.get("recipient") or payload.get("recipient_did"),
        response_status=payload.get("response_status") or payload.get("status"),
        response=payload.get("response") or payload.get("body"),
        blocked_by_cap=bool(payload.get("blocked_by_cap")),
        error=payload.get("error"),
    )
