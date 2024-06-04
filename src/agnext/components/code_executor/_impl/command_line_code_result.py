from dataclasses import dataclass
from typing import Optional

from .._base import CodeResult


@dataclass
class CommandLineCodeResult(CodeResult):
    """A code result class for command line code executor."""

    code_file: Optional[str]
