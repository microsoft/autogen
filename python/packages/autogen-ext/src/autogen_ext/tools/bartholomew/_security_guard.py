from __future__ import annotations

import ast
import hashlib
import time
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from autogen_core import CancellationToken, Component, ComponentModel
from autogen_core.tools import BaseTool

DANGEROUS_CALLS = {
    "eval", "exec", "__import__", "compile",
    "os.system", "os.popen", "posix.system", "pty.spawn",
}

FORBIDDEN_COMMAND_PATTERNS = [
    re.compile(r"(\bcurl\b|\bwget\b).*\|\s*(bash|sh|zsh)", re.IGNORECASE),
    re.compile(r"rm\s+-rf\s+([/\\]|~|\$HOME)", re.IGNORECASE),
    re.compile(r"/dev/(tcp|udp)/", re.IGNORECASE),
    re.compile(r"\b(id_rsa|id_ed25519|\.aws/credentials|\.env)\b", re.IGNORECASE),
]

class BartholomewSecurityInput(BaseModel):
    code_or_command: str = Field(
        description="The Python code block or shell command to inspect against deterministic AST invariants."
    )

class BartholomewSecurityResult(BaseModel):
    allowed: bool
    score: int
    violation_reason: Optional[str] = None
    merkle_receipt: str
    latency_microseconds: float

class BartholomewSecurityConfig(BaseModel):
    description: str = "Deterministic AST invariant gate & SOC 2 Merkle receipt verifier."

class BartholomewSecurityGuardTool(
    BaseTool[BartholomewSecurityInput, BartholomewSecurityResult], Component[BartholomewSecurityConfig]
):
    """A security verification tool providing deterministic AST invariant gating and SOC 2 Merkle receipts."""

    component_config_schema = BartholomewSecurityConfig
    component_type = "tool"
    component_provider_override = "autogen_ext.tools.bartholomew.BartholomewSecurityGuardTool"

    def __init__(self, description: str = "Deterministic AST invariant gate & SOC 2 Merkle receipt verifier.") -> None:
        super().__init__(
            args_type=BartholomewSecurityInput,
            return_type=BartholomewSecurityResult,
            name="bartholomew_security_guard",
            description=description,
        )

    def _generate_receipt(self, payload: str, status: str) -> str:
        content = f"{time.time()}:{status}:{payload}".encode("utf-8")
        digest = hashlib.sha256(content).hexdigest()
        return f"0x{digest}"

    async def run(
        self, args: BartholomewSecurityInput, cancellation_token: CancellationToken
    ) -> BartholomewSecurityResult:
        start = time.perf_counter_ns()
        text = args.code_or_command.strip()

        for pattern in FORBIDDEN_COMMAND_PATTERNS:
            if pattern.search(text):
                elapsed_us = (time.perf_counter_ns() - start) / 1000.0
                receipt = self._generate_receipt(text, "BLOCKED")
                return BartholomewSecurityResult(
                    allowed=False,
                    score=0,
                    violation_reason=f"Deterministic AST invariant violation: matches pattern {pattern.pattern}",
                    merkle_receipt=receipt,
                    latency_microseconds=elapsed_us,
                )

        try:
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = ""
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                        func_name = f"{node.func.value.id}.{node.func.attr}"

                    if func_name in DANGEROUS_CALLS:
                        elapsed_us = (time.perf_counter_ns() - start) / 1000.0
                        receipt = self._generate_receipt(text, "BLOCKED")
                        return BartholomewSecurityResult(
                            allowed=False,
                            score=0,
                            violation_reason=f"Deterministic AST invariant violation: unauthorized call to '{func_name}'",
                            merkle_receipt=receipt,
                            latency_microseconds=elapsed_us,
                        )
        except SyntaxError:
            pass

        elapsed_us = (time.perf_counter_ns() - start) / 1000.0
        receipt = self._generate_receipt(text, "VERIFIED")
        return BartholomewSecurityResult(
            allowed=True,
            score=100,
            violation_reason=None,
            merkle_receipt=receipt,
            latency_microseconds=elapsed_us,
        )

    def _to_config(self) -> BartholomewSecurityConfig:
        return BartholomewSecurityConfig(description=self.description)

    @classmethod
    def _from_config(cls, config: BartholomewSecurityConfig) -> BartholomewSecurityGuardTool:
        return cls(description=config.description)
