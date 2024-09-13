from autogen_core.components.code_executor import extract_markdown_code_blocks


def test_extract_markdown_code_blocks() -> None:
    text = """# This is a markdown text
```python
print("Hello World")
```
"""

    code_blocks = extract_markdown_code_blocks(text)

    assert len(code_blocks) == 1
    assert code_blocks[0].language == "python"
    assert code_blocks[0].code == 'print("Hello World")\n'

    text = """More markdown text
```python
print("Hello World")
```

Another code block.

```python
print("Hello World 2")
```
"""

    code_blocks = extract_markdown_code_blocks(text)

    assert len(code_blocks) == 2
    assert code_blocks[0].language == "python"
    assert code_blocks[0].code == 'print("Hello World")\n'
    assert code_blocks[1].language == "python"
    assert code_blocks[1].code == 'print("Hello World 2")\n'
