import json
import os
import sys

from autogenbench.tabulate_cmd import default_tabulate


def scorer(instance_dir):
    checker_messages = os.path.join(instance_dir, "checker_messages.json")
    if os.path.isfile(checker_messages):
        with open(checker_messages, "rt") as fh:
            messages = json.loads(fh.read())["checker_proxy"]
            results = messages[-1]["content"].lower()
            if "the answer is correct" in results or "the answer is approximated but should be correct" in results:
                return True
            else:
                return False
    else:
        return None


def main(args):
    default_tabulate(args, scorer=scorer)


if __name__ == "__main__" and __package__ is None:
    main(sys.argv)
