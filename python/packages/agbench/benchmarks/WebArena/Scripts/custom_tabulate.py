import os
import sys
import re
from agbench.tabulate_cmd import default_tabulate


def scorer(instance_dir):

    # Read the console
    console_log_file = os.path.join(instance_dir, "console_log.txt")
    if not os.path.isfile(console_log_file):
        return None

    console_log = ""
    with open(console_log_file, "rt") as fh:
        console_log = fh.read()

        final_score = None 
        m = re.search(r"FINAL SCORE:(.*?)\n", console_log, re.DOTALL)
        if m:
            final_score = m.group(1).strip()

        # Missing the final answer line
        if final_score is None:
            return None
        else:
            return float(final_score) > 0


def main(args):
    default_tabulate(args, scorer=scorer)


if __name__ == "__main__" and __package__ is None:
    main(sys.argv)
