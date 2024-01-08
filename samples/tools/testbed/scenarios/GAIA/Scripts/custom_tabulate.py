import os
import sys
import json
import re
from autogenbench.tabulate_cmd import default_tabulate


def normalize_answer(a):
    # Lower case
    # Trim (left and right)
    # Replace multiple spaces with one space
    # Remove trailing punctuation
    return re.sub(r"[\.\!\?]+$", "", re.sub(r"\s+", " ", a.strip().lower()))


def scorer(instance_dir):
    # Read the expected answer
    expected_answer_file = os.path.join(instance_dir, "expected_answer.txt")
    if not os.path.isfile(expected_answer_file):
        return None

    expected_answer = None
    with open(expected_answer_file, "rt") as fh:
        expected_answer = fh.read().strip()

    # Read the console
    console_log_file = os.path.join(instance_dir, "console_log.txt")
    if not os.path.isfile(console_log_file):
        return None

    console_log = ""
    with open(console_log_file, "rt") as fh:
        console_log = fh.read()

        final_answer = ""
        m = re.search(r"FINAL ANSWER:(.*?)\n", console_log, re.DOTALL)
        if m:
            final_answer = m.group(1).strip()

        # Return true if they are equal after normalization
        return normalize_answer(expected_answer) == normalize_answer(final_answer)


def main(args):
    default_tabulate(args, scorer=scorer)


if __name__ == "__main__" and __package__ is None:
    main(sys.argv)
