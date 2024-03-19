# Disable ruff linter for incomplete template files
# ruff: noqa: F821

import glob
import os
import subprocess
import sys
import shutil
import json


def scoring(content: str, should_contain: list, should_not_contain: list):
    is_case_sensitive = __CASE_SENSITIVE__

    print("\033[1;34mScoring content:\033[0m\n", content)
    if should_contain:
        for should_contain_word in should_contain:
            if not is_case_sensitive:
                should_contain_word = should_contain_word.lower()
                content = content.lower()
            if should_contain_word not in content:
                # print(print_content)
                return 0.0

    if should_not_contain:
        for should_not_contain_word in should_not_contain:
            if not is_case_sensitive:
                should_not_contain_word = should_not_contain_word.lower()
                content = content.lower()
            if should_not_contain_word in content:
                return 0.0
    return 1.0


def check():
    files_contents = []
    scores = []

    file_pattern = "__FILE_PATTERN__"
    eval_type = "__EVAL_TYPE__"

    with open("../should_contain.json.txt", "r") as f:
        should_contain = json.loads(f.read())
        assert isinstance(should_contain, list), "TERMINATE\n"

    with open("../should_not_contain.json.txt", "r") as f:
        should_not_contain = json.loads(f.read())
        assert isinstance(should_not_contain, list), "TERMINATE\n"

    # Check if file pattern is a file extension
    if file_pattern.startswith("."):
        # Find all files with the given extension in the workspace
        matching_files = glob.glob(os.path.join("*" + file_pattern))
    else:
        matching_files = [file_pattern]

    for file_path in matching_files:
        if eval_type == "python":
            # copy the test file to working directory
            shutil.copy(f"../custom_python/{file_path}", "./")
            result = subprocess.run(
                [sys.executable, file_path],
                cwd=os.path.abspath("./"),
                capture_output=True,
                text=True,
            )
            if "error" in result.stderr or result.returncode != 0:
                print(result.stderr)
                assert False, result.stderr
            files_contents.append(f"Output: {result.stdout}\n")
        elif eval_type == "file":
            with open(file_path, "r") as f:
                files_contents.append(f.read())
        else:
            raise Exception(
                f"eval_type {eval_type} currently not supported! (only python, file is supported) TERMINATE\n"
            )

    for content in files_contents:
        score = scoring(content, should_contain, should_not_contain)
        scores.append(score)

    if 1.0 in scores:
        print("ALL TESTS PASSED !#!#\n\nTERMINATE")
    else:
        print("TEST FAILED !#!#")


if __name__ == "__main__":
    check()
