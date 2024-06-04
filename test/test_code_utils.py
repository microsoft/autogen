#!/usr/bin/env python3 -m pytest

import os
import sys
import tempfile
import unittest
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from conftest import skip_docker

import autogen
from autogen.code_utils import (
    UNKNOWN,
    check_can_use_docker_or_throw,
    content_str,
    create_virtual_env,
    decide_use_docker,
    execute_code,
    extract_code,
    get_powershell_command,
    improve_code,
    improve_function,
    in_docker_container,
    infer_lang,
    is_docker_running,
)

KEY_LOC = "notebook"
OAI_CONFIG_LIST = "OAI_CONFIG_LIST"
here = os.path.abspath(os.path.dirname(__file__))

if skip_docker or not is_docker_running() or not decide_use_docker(use_docker=None):
    skip_docker_test = True
else:
    skip_docker_test = False


# def test_find_code():
#     try:
#         import openai
#     except ImportError:
#         return
#     # need gpt-4 for this task
#     config_list = autogen.config_list_from_json(
#         OAI_CONFIG_LIST,
#         file_location=KEY_LOC,
#         filter_dict={
#             "model": ["gpt-4", "gpt4", "gpt-4-32k", "gpt-4-32k-0314"],
#         },
#     )
#     # config_list = autogen.config_list_from_json(
#     #     OAI_CONFIG_LIST,
#     #     file_location=KEY_LOC,
#     #     filter_dict={
#     #         "model": {
#     #             "gpt-3.5-turbo",
#     #             "gpt-3.5-turbo-16k",
#     #             "gpt-3.5-turbo-16k-0613",
#     #             "gpt-3.5-turbo-0301",
#     #             "chatgpt-35-turbo-0301",
#     #             "gpt-35-turbo-v0301",
#     #         },
#     #     },
#     # )
#     seed = 42
#     messages = [
#         {
#             "role": "user",
#             "content": "Print hello world to a file called hello.txt",
#         },
#         {
#             "role": "user",
#             "content": """
# # filename: write_hello.py
# ```
# with open('hello.txt', 'w') as f:
#     f.write('Hello, World!')
# print('Hello, World! printed to hello.txt')
# ```
# Please execute the above Python code to print "Hello, World!" to a file called hello.txt and print the success message.
# """,
#         },
#     ]
#     codeblocks, _ = find_code(messages, seed=seed, config_list=config_list)
#     assert codeblocks[0][0] == "python", codeblocks
#     messages += [
#         {
#             "role": "user",
#             "content": """
# exitcode: 0 (execution succeeded)
# Code output:
# Hello, World! printed to hello.txt
# """,
#         },
#         {
#             "role": "assistant",
#             "content": "Great! Can I help you with anything else?",
#         },
#     ]
#     codeblocks, content = find_code(messages, seed=seed, config_list=config_list)
#     assert codeblocks[0][0] == "unknown", content
#     messages += [
#         {
#             "role": "user",
#             "content": "Save a pandas df with 3 rows and 3 columns to disk.",
#         },
#         {
#             "role": "assistant",
#             "content": """
# ```
# # filename: save_df.py
# import pandas as pd

# df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
# df.to_csv('df.csv')
# print('df saved to df.csv')
# ```
# Please execute the above Python code to save a pandas df with 3 rows and 3 columns to disk.
# Before you run the code above, run
# ```
# pip install pandas
# ```
# first to install pandas.
# """,
#         },
#     ]
#     codeblocks, content = find_code(messages, seed=seed, config_list=config_list)
#     assert (
#         len(codeblocks) == 2
#         and (codeblocks[0][0] == "sh"
#         and codeblocks[1][0] == "python"
#         or codeblocks[0][0] == "python"
#         and codeblocks[1][0] == "sh")
#     ), content

#     messages += [
#         {
#             "role": "user",
#             "content": "The code is unsafe to execute in my environment.",
#         },
#         {
#             "role": "assistant",
#             "content": "please run python write_hello.py",
#         },
#     ]
#     # codeblocks, content = find_code(messages, config_list=config_list)
#     # assert codeblocks[0][0] != "unknown", content
#     # I'm sorry, but I cannot execute code from earlier messages. Please provide the code again if you would like me to execute it.

#     messages[-1]["content"] = "please skip pip install pandas if you already have pandas installed"
#     codeblocks, content = find_code(messages, seed=seed, config_list=config_list)
#     assert codeblocks[0][0] != "sh", content

#     messages += [
#         {
#             "role": "user",
#             "content": "The code is still unsafe to execute in my environment.",
#         },
#         {
#             "role": "assistant",
#             "content": "Let me try something else. Do you have docker installed?",
#         },
#     ]
#     codeblocks, content = find_code(messages, seed=seed, config_list=config_list)
#     assert codeblocks[0][0] == "unknown", content
#     print(content)


def test_infer_lang():
    assert infer_lang("print('hello world')") == "python"
    assert infer_lang("pip install autogen") == "sh"

    # test infer lang for unknown code/invalid code
    assert infer_lang("dummy text") == UNKNOWN
    assert infer_lang("print('hello world'))") == UNKNOWN


def test_extract_code():
    print(extract_code("```bash\npython temp.py\n```"))
    # test extract_code from markdown
    codeblocks = extract_code(
        """
Example:
```
print("hello extract code")
```
""",
        detect_single_line_code=False,
    )
    print(codeblocks)

    codeblocks2 = extract_code(
        """
Example:
```
print("hello extract code")
```
""",
        detect_single_line_code=True,
    )
    print(codeblocks2)

    assert codeblocks2 == codeblocks
    # import pdb; pdb.set_trace()

    codeblocks = extract_code(
        """
Example:
```python
def scrape(url):
    import requests
    from bs4 import BeautifulSoup
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.find("title").text
    text = soup.find("div", {"id": "bodyContent"}).text
    return title, text
```
Test:
```python
url = "https://en.wikipedia.org/wiki/Web_scraping"
title, text = scrape(url)
print(f"Title: {title}")
print(f"Text: {text}")
```
"""
    )
    print(codeblocks)
    assert len(codeblocks) == 2 and codeblocks[0][0] == "python" and codeblocks[1][0] == "python"

    codeblocks = extract_code(
        """
Example:
``` python
def scrape(url):
    import requests
    from bs4 import BeautifulSoup
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.find("title").text
    text = soup.find("div", {"id": "bodyContent"}).text
    return title, text
```
Test:
``` python
url = "https://en.wikipedia.org/wiki/Web_scraping"
title, text = scrape(url)
print(f"Title: {title}")
print(f"Text: {text}")
```
"""
    )
    print(codeblocks)
    assert len(codeblocks) == 2 and codeblocks[0][0] == "python" and codeblocks[1][0] == "python"

    # Check for indented code blocks
    codeblocks = extract_code(
        """
Example:
   ```python
   def scrape(url):
       import requests
       from bs4 import BeautifulSoup
       response = requests.get(url)
       soup = BeautifulSoup(response.text, "html.parser")
       title = soup.find("title").text
       text = soup.find("div", {"id": "bodyContent"}).text
       return title, text
   ```
"""
    )
    print(codeblocks)
    assert len(codeblocks) == 1 and codeblocks[0][0] == "python"

    # Check for codeblocks with \r\n
    codeblocks = extract_code(
        """
Example:
``` python
def scrape(url):
   import requests
   from bs4 import BeautifulSoup
   response = requests.get(url)
   soup = BeautifulSoup(response.text, "html.parser")
   title = soup.find("title").text
   text = soup.find("div", {"id": "bodyContent"}).text
   return title, text
```
""".replace(
            "\n", "\r\n"
        )
    )
    print(codeblocks)
    assert len(codeblocks) == 1 and codeblocks[0][0] == "python"

    codeblocks = extract_code("no code block")
    assert len(codeblocks) == 1 and codeblocks[0] == (UNKNOWN, "no code block")

    # Disable single line code detection
    line = "Run `source setup.sh` from terminal"
    codeblocks = extract_code(line, detect_single_line_code=False)
    assert len(codeblocks) == 1 and codeblocks[0] == (UNKNOWN, line)

    # Enable single line code detection
    codeblocks = extract_code("Run `source setup.sh` from terminal", detect_single_line_code=True)
    assert len(codeblocks) == 1 and codeblocks[0] == ("", "source setup.sh")


@pytest.mark.skipif(skip_docker_test, reason="docker is not running or requested to skip docker tests")
def test_execute_code(use_docker=True):
    # Test execute code and save the code to a file.
    with tempfile.TemporaryDirectory() as tempdir:
        filename = "temp_file_with_code.py"

        # execute code and save the code to a file.
        exit_code, msg, image = execute_code(
            "print('hello world')",
            filename=filename,
            work_dir=tempdir,
            use_docker=use_docker,
        )
        assert exit_code == 0 and msg == "hello world\n", msg

        # read the file just saved
        exit_code, msg, image = execute_code(
            f"with open('{filename}', 'rt') as f: print(f.read())",
            use_docker=use_docker,
            work_dir=tempdir,
        )
        assert exit_code == 0 and "print('hello world')" in msg, msg

        # execute code in a file
        exit_code, msg, image = execute_code(
            filename=filename,
            use_docker=use_docker,
            work_dir=tempdir,
        )
        assert exit_code == 0 and msg == "hello world\n", msg

        # execute code in a file using shell command directly
        exit_code, msg, image = execute_code(
            f"python {filename}",
            lang="sh",
            use_docker=use_docker,
            work_dir=tempdir,
        )
        assert exit_code == 0 and msg == "hello world\n", msg

    with tempfile.TemporaryDirectory() as tempdir:
        # execute code for assertion error
        exit_code, msg, image = execute_code(
            "assert 1==2",
            use_docker=use_docker,
            work_dir=tempdir,
        )
        assert exit_code, msg
        assert "AssertionError" in msg
        assert 'File "' in msg or 'File ".\\"' in msg  # py3.8 + win32

    with tempfile.TemporaryDirectory() as tempdir:
        # execute code which takes a long time
        exit_code, error, image = execute_code(
            "import time; time.sleep(2)",
            timeout=1,
            use_docker=use_docker,
            work_dir=tempdir,
        )
        assert exit_code and error == "Timeout"
        if use_docker is True:
            assert isinstance(image, str)


@pytest.mark.skipif(skip_docker_test, reason="docker is not running or requested to skip docker tests")
def test_execute_code_with_custom_filename_on_docker():
    with tempfile.TemporaryDirectory() as tempdir:
        filename = "codetest.py"
        exit_code, msg, image = execute_code(
            "print('hello world')",
            filename=filename,
            use_docker=True,
            work_dir=tempdir,
        )
        assert exit_code == 0 and msg == "hello world\n", msg
        assert image == "python:codetest.py"


@pytest.mark.skipif(
    skip_docker_test,
    reason="docker is not running or requested to skip docker tests",
)
def test_execute_code_with_misformed_filename_on_docker():
    with tempfile.TemporaryDirectory() as tempdir:
        filename = "codetest.py (some extra information)"
        exit_code, msg, image = execute_code(
            "print('hello world')",
            filename=filename,
            use_docker=True,
            work_dir=tempdir,
        )
        assert exit_code == 0 and msg == "hello world\n", msg
        assert image == "python:codetest.py__some_extra_information_"


def test_execute_code_raises_when_code_and_filename_are_both_none():
    with pytest.raises(AssertionError):
        execute_code(code=None, filename=None)


def test_execute_code_no_docker():
    test_execute_code(use_docker=False)


def test_execute_code_timeout_no_docker():
    exit_code, error, image = execute_code("import time; time.sleep(2)", timeout=1, use_docker=False)
    assert exit_code and error == "Timeout"
    assert image is None


def get_current_autogen_env_var():
    return os.environ.get("AUTOGEN_USE_DOCKER", None)


def restore_autogen_env_var(current_env_value):
    if current_env_value is None:
        del os.environ["AUTOGEN_USE_DOCKER"]
    else:
        os.environ["AUTOGEN_USE_DOCKER"] = current_env_value


def test_decide_use_docker_truthy_values():
    current_env_value = get_current_autogen_env_var()

    for truthy_value in ["1", "true", "yes", "t"]:
        os.environ["AUTOGEN_USE_DOCKER"] = truthy_value
        assert decide_use_docker(None) is True

    restore_autogen_env_var(current_env_value)


def test_decide_use_docker_falsy_values():
    current_env_value = get_current_autogen_env_var()

    for falsy_value in ["0", "false", "no", "f"]:
        os.environ["AUTOGEN_USE_DOCKER"] = falsy_value
        assert decide_use_docker(None) is False

    restore_autogen_env_var(current_env_value)


def test_decide_use_docker():
    current_env_value = get_current_autogen_env_var()

    os.environ["AUTOGEN_USE_DOCKER"] = "none"
    assert decide_use_docker(None) is None
    os.environ["AUTOGEN_USE_DOCKER"] = "invalid"
    with pytest.raises(ValueError):
        decide_use_docker(None)

    restore_autogen_env_var(current_env_value)


def test_decide_use_docker_with_env_var():
    current_env_value = get_current_autogen_env_var()

    os.environ["AUTOGEN_USE_DOCKER"] = "false"
    assert decide_use_docker(None) is False
    os.environ["AUTOGEN_USE_DOCKER"] = "true"
    assert decide_use_docker(None) is True
    os.environ["AUTOGEN_USE_DOCKER"] = "none"
    assert decide_use_docker(None) is None
    os.environ["AUTOGEN_USE_DOCKER"] = "invalid"
    with pytest.raises(ValueError):
        decide_use_docker(None)

    restore_autogen_env_var(current_env_value)


def test_decide_use_docker_with_env_var_and_argument():
    current_env_value = get_current_autogen_env_var()

    os.environ["AUTOGEN_USE_DOCKER"] = "false"
    assert decide_use_docker(True) is True
    os.environ["AUTOGEN_USE_DOCKER"] = "true"
    assert decide_use_docker(False) is False
    os.environ["AUTOGEN_USE_DOCKER"] = "none"
    assert decide_use_docker(True) is True
    os.environ["AUTOGEN_USE_DOCKER"] = "invalid"
    assert decide_use_docker(True) is True

    restore_autogen_env_var(current_env_value)


def test_can_use_docker_or_throw():
    check_can_use_docker_or_throw(None)
    if not is_docker_running() and not in_docker_container():
        check_can_use_docker_or_throw(False)
    if not is_docker_running() and not in_docker_container():
        with pytest.raises(RuntimeError):
            check_can_use_docker_or_throw(True)


def test_create_virtual_env():
    with tempfile.TemporaryDirectory() as temp_dir:
        venv_context = create_virtual_env(temp_dir)
        assert isinstance(venv_context, SimpleNamespace)
        assert venv_context.env_name == os.path.split(temp_dir)[1]


def test_create_virtual_env_with_extra_args():
    with tempfile.TemporaryDirectory() as temp_dir:
        venv_context = create_virtual_env(temp_dir, with_pip=False)
        assert isinstance(venv_context, SimpleNamespace)
        assert venv_context.env_name == os.path.split(temp_dir)[1]


def _test_improve():
    try:
        import openai
    except ImportError:
        return
    config_list = autogen.config_list_openai_aoai(KEY_LOC)
    improved, _ = improve_function(
        "autogen/math_utils.py",
        "solve_problem",
        "Solve math problems accurately, by avoiding calculation errors and reduce reasoning errors.",
        config_list=config_list,
    )
    with open(f"{here}/math_utils.py.improved", "w") as f:
        f.write(improved)
    suggestion, _ = improve_code(
        ["autogen/code_utils.py", "autogen/math_utils.py"],
        "leverage generative AI smartly and cost-effectively",
        config_list=config_list,
    )
    print(suggestion)
    improvement, cost = improve_code(
        ["autogen/code_utils.py", "autogen/math_utils.py"],
        "leverage generative AI smartly and cost-effectively",
        suggest_only=False,
        config_list=config_list,
    )
    print(cost)
    with open(f"{here}/suggested_improvement.txt", "w") as f:
        f.write(improvement)


class TestContentStr(unittest.TestCase):
    def test_string_content(self):
        self.assertEqual(content_str("simple string"), "simple string")

    def test_list_of_text_content(self):
        content = [{"type": "text", "text": "hello"}, {"type": "text", "text": " world"}]
        self.assertEqual(content_str(content), "hello world")

    def test_mixed_content(self):
        content = [{"type": "text", "text": "hello"}, {"type": "image_url", "url": "http://example.com/image.png"}]
        self.assertEqual(content_str(content), "hello<image>")

    def test_invalid_content(self):
        content = [{"type": "text", "text": "hello"}, {"type": "wrong_type", "url": "http://example.com/image.png"}]
        with self.assertRaises(ValueError) as context:
            content_str(content)
        self.assertIn("Wrong content format", str(context.exception))

    def test_empty_list(self):
        self.assertEqual(content_str([]), "")

    def test_non_dict_in_list(self):
        content = ["string", {"type": "text", "text": "text"}]
        with self.assertRaises(TypeError):
            content_str(content)


class TestGetPowerShellCommand(unittest.TestCase):
    @patch("subprocess.run")
    def test_get_powershell_command_powershell(self, mock_subprocess_run):
        # Set up the mock to return a successful result for 'powershell'
        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stdout = StringIO("5")

        self.assertEqual(get_powershell_command(), "powershell")

    @patch("subprocess.run")
    def test_get_powershell_command_pwsh(self, mock_subprocess_run):
        # Set up the mock to return a successful result for 'pwsh'
        mock_subprocess_run.side_effect = [FileNotFoundError, mock_subprocess_run.return_value]
        mock_subprocess_run.return_value.returncode = 0
        mock_subprocess_run.return_value.stdout = StringIO("7")

        self.assertEqual(get_powershell_command(), "pwsh")

    @patch("subprocess.run")
    def test_get_powershell_command_not_found(self, mock_subprocess_run):
        mock_subprocess_run.side_effect = [FileNotFoundError, FileNotFoundError]
        with self.assertRaises(FileNotFoundError):
            get_powershell_command()

    @patch("subprocess.run")
    def test_get_powershell_command_no_permission(self, mock_subprocess_run):
        mock_subprocess_run.side_effect = [PermissionError, FileNotFoundError]
        with self.assertRaises(PermissionError):
            get_powershell_command()


if __name__ == "__main__":
    # test_infer_lang()
    test_extract_code()
    # test_execute_code()
    # test_find_code()
    # unittest.main()
