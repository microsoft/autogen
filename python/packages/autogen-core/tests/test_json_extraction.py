import pytest
from autogen_core.utils import extract_json_from_str

def test_extract_json_from_str():
  json_str = """
  {
    "name": "John",
    "age": 30,
    "city": "New York"
  }
  """
  json_resp = [{
    "name": "John",
    "age": 30,
    "city": "New York"
  }]
  resp = extract_json_from_str(json_str)
  assert resp == json_resp
  
  invalid_json_str = """
  {
    "name": "John",
    "age": 30,
    "city": "New York"
  """
  with pytest.raises(ValueError):
    extract_json_from_str(invalid_json_str)
  
def test_extract_json_from_str_codeblock():
  code_block_lang_str = """
  ```json
  {
    "name": "Alice",
    "age": 28,
    "city": "Seattle"
  }
  ```
  """
  code_block_no_lang_str = """
  ```
  {
    "name": "Alice",
    "age": 28,
    "city": "Seattle"
  }
  ```
  """
  code_block_resp = [{
    "name": "Alice",
    "age": 28,
    "city": "Seattle"
  }]
  multi_json_str = """
  ```json
  {
    "name": "John",
    "age": 30,
    "city": "New York"
  }
  ```
  ```json
  {
    "name": "Jane",
    "age": 25,
    "city": "Los Angeles"
  }
  ```
  """
  multi_json_resp = [
    {
      "name": "John",
      "age": 30,
      "city": "New York"
    },
    {
      "name": "Jane",
      "age": 25,
      "city": "Los Angeles"
    }
  ]

  lang_resp = extract_json_from_str(code_block_lang_str)
  assert lang_resp == code_block_resp
  no_lang_resp = extract_json_from_str(code_block_no_lang_str)
  assert no_lang_resp == code_block_resp
  multi_resp = extract_json_from_str(multi_json_str)
  assert multi_resp == multi_json_resp
  
  invalid_lang_code_block_str = """
  ```notjson
  {
    "name": "Alice",
    "age": 28,
    "city": "Seattle"
  }
  """
  with pytest.raises(ValueError):
    extract_json_from_str(invalid_lang_code_block_str)