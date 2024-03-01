import asyncio
import logging
from collections import defaultdict
from typing import Dict, List, Any, Set, Tuple
from dataclasses import dataclass
from .utils import consolidate_chat_info
import warnings

try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x


logger = logging.getLogger(__name__)
Prerequisite = Tuple[int, int]


@dataclass
class Task:
    """(Experimental) Information about a task."""

    description: str = None
    """A description of the task in string."""
    solution: Any = None
    completion_eval: callable = None
    """A function to evaluate the completion of the task.
    The function should return a tuple of (complete, score),
    where complete is a boolean indicating if the task is completed,
    and score is a float indicating the score of the completion.
    Example:
    ```python
    def completion_eval(chat_history, work_dir) -> Tuple[bool, float]:
        # check if a file is created in a working directory
        complete = os.path.exists(os.path.join(work_dir, "result.md"))

        # read the result from a file in a working directory and check if it contains a specific string
        with open(os.path.join(work_dir, "result.md"), "r") as f:
            result = f.read()
        score = 1 if "success" in result else 0
        return complete, score
    ```
    """
