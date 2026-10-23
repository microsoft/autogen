import sys
import os

# Add path to autogen_core
sys.path.append(os.path.abspath("python/packages/autogen-core/src"))

from autogen_core.utils.sanitizer import sanitize_tool_calls

def test_valid():
    message = {"content": "All good", "tool_calls": [{"name": "tool1"}]}
    assert sanitize_tool_calls(message) == message
    print(" Valid message passed.")

def test_empty_tool_calls():
    try:
        sanitize_tool_calls({"content": "nothing", "tool_calls": []})
    except ValueError as e:
        print(f" Caught expected error: {e}")

def test_tool_call_end_only():
    try:
        sanitize_tool_calls({"content": "<|tool_call_end|>"})
    except ValueError as e:
        print(f" Caught expected error: {e}")

if __name__ == "__main__":
    test_valid()
    test_empty_tool_calls()
    test_tool_call_end_only()
