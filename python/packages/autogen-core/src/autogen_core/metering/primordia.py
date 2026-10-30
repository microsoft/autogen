"""Primordia metering for AutoGen conversations."""
import hashlib
import json
import time
from typing import Dict, List


class PrimordiaMetering:
    """Track AutoGen conversation costs with MSR receipts.

    Shadow mode by default - no network calls, no blocking.

    Example:
        >>> from autogen_core.metering import PrimordiaMetering
        >>> meter = PrimordiaMetering(agent_id="autogen-conv-1")
        >>> meter.record_message("assistant", 1500, "gpt-4")
        >>> print(f"Cost: ${meter.get_total_cost():.4f}")
    """

    def __init__(self, agent_id: str, kernel_url: str = "https://clearing.kaledge.app"):
        self.agent_id = agent_id
        self.kernel_url = kernel_url
        self.receipts: List[Dict] = []

    def record_message(
        self,
        sender: str,
        tokens: int,
        model: str = "gpt-4",
    ) -> str:
        """Record a message as MSR receipt."""
        unit_price = 300 if "gpt-4" in model.lower() else 50
        if "claude" in model.lower():
            unit_price = 100

        receipt = {
            "meter_version": "0.1",
            "type": "compute",
            "agent_id": self.agent_id,
            "provider": model,
            "units": tokens,
            "unit_price_usd_micros": unit_price,
            "total_usd_micros": tokens * unit_price,
            "timestamp_ms": int(time.time() * 1000),
            "metadata": {"framework": "autogen", "sender": sender}
        }

        receipt_hash = hashlib.sha256(
            json.dumps(receipt, sort_keys=True).encode()
        ).hexdigest()[:32]

        self.receipts.append({"hash": receipt_hash, "receipt": receipt})
        return receipt_hash

    def get_total_cost(self) -> float:
        """Get total conversation cost in USD."""
        return sum(r["receipt"]["total_usd_micros"] for r in self.receipts) / 1_000_000

    def get_receipts(self) -> List[Dict]:
        """Get all receipts for settlement."""
        return self.receipts
