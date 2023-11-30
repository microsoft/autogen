import base64
import glob
import os
import subprocess
import sys


def scoring(content: str, should_contain: list, should_not_contain: list):
    print("\033[1;34mScoring content:\033[0m", content)
    if should_contain:
        for should_contain_word in should_contain:
            if not "__CASE_SENSITIVE__" == "True":
                should_contain_word = should_contain_word.lower()
                content = content.lower()
            if should_contain_word not in content:
                # print(print_content)
                return 0.0

    if should_not_contain:
        for should_not_contain_word in should_not_contain:
            if not "__CASE_SENSITIVE__" == "True":
                should_not_contain_word = should_not_contain_word.lower()
                content = content.lower()
            # print_content = f"\033[1;34mWord that should not exist\033[0m - {should_not_contain_word}:"
            if should_not_contain_word in content:
                return 0.0
    return 1.0


def check():
    workspace = "coding"
    files_contents = []
    scores = []

    file_pattern = "__FILE_PATTERN__"
    eval_type = "__EVAL_TYPE__"

    with open("../should_contain.txt", "r") as f:
        should_contain = eval(f.read())
        assert type(should_contain) == list, "TERMINATE\n"
        should_contain = [base64.b64decode(encoded).decode("utf-8") for encoded in should_contain]

    with open("../should_not_contain.txt", "r") as f:
        should_not_contain = eval(f.read())
        assert type(should_not_contain) == list, "TERMINATE\n"
        should_not_contain = [base64.b64decode(encoded).decode("utf-8") for encoded in should_not_contain]

    # Check if file pattern is a file extension
    if file_pattern.startswith("."):
        # Find all files with the given extension in the workspace
        matching_files = glob.glob(os.path.join("*" + file_pattern))
    else:
        matching_files = [file_pattern]

    for file_path in matching_files:
        if eval_type == "python":
            result = subprocess.run(
                [sys.executable, file_path],
                cwd=os.path.abspath(workspace),
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
        # print("\033[1;34mScoring content:\033[0m", content)
        score = scoring(content, should_contain, should_not_contain)
        scores.append(score)

    if 1.0 in scores:
        print("ALL TESTS PASSED!\n\nTERMINATE.")
    else:
        print("Test failed.")


check()
