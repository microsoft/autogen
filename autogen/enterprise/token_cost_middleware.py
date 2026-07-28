from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


@dataclass
class TokenPricing:
    input_per_1k: float
    output_per_1k: float


DEFAULT_PRICING: Dict[str, TokenPricing] = {
    "gpt-4o": TokenPricing(2.5, 5.0),
    "gpt-4o-mini": TokenPricing(0.15, 0.6),
}


def _estimate_tokens(text: str) -> int:
    # Fallback lightweight estimate to avoid heavy deps.
    # ~4 chars per token heuristic.
    return max(1, len(text) // 4)


@dataclass
class TokenCostRecord:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    input_cost_usd: float = 0.0
    output_cost_usd: float = 0.0

    @property
    def total_cost_usd(self) -> float:
        return self.input_cost_usd + self.output_cost_usd


class TokenCostMiddleware:
    """Middleware to compute token counts and cost for messages.

    Hook points:
      - on_request(prompt, model)
      - on_response(text, model)
    Aggregates per-call cost and exposes a callback for reporting.
    """

    def __init__(self, pricing: Optional[Dict[str, TokenPricing]] = None, on_record: Optional[Callable[[TokenCostRecord], None]] = None) -> None:
        self.pricing = pricing or DEFAULT_PRICING
        self.on_record = on_record

    def on_request(self, prompt: str, model: str) -> Dict[str, Any]:
        itoks = _estimate_tokens(prompt)
        pr = self.pricing.get(model)
        icost = (itoks / 1000.0) * (pr.input_per_1k if pr else 0.0)
        return {"_tc_itoks": itoks, "_tc_icost": icost, "_tc_model": model}

    def on_response(self, text: str, context: Dict[str, Any]) -> TokenCostRecord:
        model = context.get("_tc_model", "")
        otoks = _estimate_tokens(text)
        pr = self.pricing.get(model)
        ocost = (otoks / 1000.0) * (pr.output_per_1k if pr else 0.0)
        rec = TokenCostRecord(model=model, input_tokens=context.get("_tc_itoks", 0), output_tokens=otoks,
                              input_cost_usd=context.get("_tc_icost", 0.0), output_cost_usd=ocost)
        if self.on_record:
            try:
                self.on_record(rec)
            except Exception:
                pass
        return rec
