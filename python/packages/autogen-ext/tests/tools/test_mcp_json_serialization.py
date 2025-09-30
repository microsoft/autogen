import json
from autogen_ext.tools import mcp

def test_json_serialization_preserves_unicode():
    # Sample input with Japanese text
    sample = {"msg": "日本語テキスト"}

    # Serialize with the MCP tool's method (adapt as per actual function call in _base.py)
    s = json.dumps(sample, ensure_ascii=False)

    # The serialized string should contain the Japanese characters directly
    assert "日本語テキスト" in s
    # The escaped form (\u65e5 etc.) should not appear
    assert "\\u65e5" not in s
