import json
import re
from typing import Any, Dict, List


def extract_json_from_str(content: str) -> List[Dict[str, Any]]:
    """Extract JSON objects from a string. Supports backtick enclosed JSON objects"""
    pattern = re.compile(r"```(?:\s*([\w\+\-]+))?\n([\s\S]*?)```")
    matches = pattern.findall(content)
    ret: List[Dict[str, Any]] = []
    # If no matches found, assume the entire content is a JSON object
    if not matches:
        ret.append(json.loads(content))
    for match in matches:
        language = match[0].strip() if match[0] else None
        if language and language.lower() != "json":
            raise ValueError(f"Expected JSON object, but found language: {language}")
        content = match[1]
        ret.append(json.loads(content))
    return ret
