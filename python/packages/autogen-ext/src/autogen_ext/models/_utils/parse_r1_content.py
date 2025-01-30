import warnings
from typing import Tuple


def parse_r1_content(content: str) -> Tuple[str | None, str]:
    """Parse the content of an R1-style message that contains a `<think>...</think>` field."""
    # Find the start and end of the think field
    think_start = content.find("<think>")
    think_end = content.find("</think>")

    # Extract the think field
    if think_start == -1 or think_end == -1:
        warnings.warn("Could not find <think>..</think> field in model response content.", UserWarning, stacklevel=2)
        return None, content

    thought = content[think_start + len("<think>") : think_end].strip()

    # Extract the rest of the content, skipping the think field.
    content = content[think_end + len("</think>") :].strip()

    return thought, content
