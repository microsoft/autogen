# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""NVIDIA NIM Speculative Reasoning Execution (SRE) Client for AutoGen 0.4.

This package provides a ChatCompletionClient that bridges NVIDIA NIM
high-performance inference with Microsoft AutoGen orchestration, enabling
parallel tool execution during LLM reasoning to reduce "Time to Action" latency.
"""

from ._nvidia_speculative_client import NvidiaSpeculativeClient
from ._reasoning_sniffer import ReasoningSniffer, ToolIntent
from ._speculative_cache import SpeculativeCache

__all__ = [
    "NvidiaSpeculativeClient",
    "ReasoningSniffer",
    "ToolIntent",
    "SpeculativeCache",
]
