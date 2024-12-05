from dataclasses import dataclass
from typing import Optional

from typing_extensions import deprecated

from ....code_executor._base import CodeResult


@deprecated(
    "CommandLineCodeResult moved to autogen_ext.code_executors.CommandLineCodeResult. This alias will be removed in 0.4.0."
)
@dataclass
class CommandLineCodeResult(CodeResult):
    """A code result class for command line code executor."""

    code_file: Optional[str]
