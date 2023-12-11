import os
import json
import re
import sys
import argparse


def normalize_answer(a):
    # Trim (left and right)
    # Replace multiple spaces with one space
    # Remove trailing punctuation
    # Trim again
    return re.sub(r"[\.\!\?]+$", "", re.sub(r"\s+", " ", a.strip())).strip()


def collate(results_dir, instance=0):
    """
    Collate the results of running GAIA. Print the results in the format acceped by the leaderboard.

    Args:
        results_dir (path): The folder were results were be saved.
    """

    for test_id in os.listdir(results_dir):
        test_path = os.path.join(results_dir, test_id)

        instance_dir = os.path.join(test_path, str(instance))
        console_log_file = os.path.join(instance_dir, "console_log.txt")

        final_answer = ""
        if os.path.isfile(console_log_file):
            with open(console_log_file, "rt") as fh:
                console_log = fh.read()

                final_answer = ""
                m = re.search(r"FINAL ANSWER:(.*?)\n", console_log, re.DOTALL)
                if m:
                    final_answer = normalize_answer(m.group(1))

        # Clean up the GAIA logs so they don't have the Docker setup preamble
        m = re.search(r"^.*?\r?\n(user_proxy \(to assistant\).*$)", console_log, re.DOTALL)
        if m:
            console_log = m.group(1)

        print(json.dumps({"task_id": test_id, "model_answer": final_answer, "reasoning_trace": console_log}))


###############################################################################
if __name__ == "__main__":
    script_path = os.path.realpath(__file__)
    script_name = os.path.basename(script_path)
    script_dir = os.path.dirname(script_path)

    # Path to the default results directory
    # (relative to this script, up on directory, then into the results folder)
    default_results_dir = os.path.realpath(
        os.path.join(script_dir, os.path.pardir, "results", "gaia_validation_level_1__two_agents_gpt4")
    )

    parser = argparse.ArgumentParser(
        description=f"""
{script_name} will collate the results of the GAIA scenarios into the jsonl format that can be submit to the GAIA leaderboard.

NOTE: You will likely need to concatenate resuls for level 1, level 2 and level 3 to form a complete submission.
""".strip(),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "scenario",
        nargs="?",
        help="Path to the scenario results. (default: " + default_results_dir + ")",
        default=default_results_dir,
    )
    args = parser.parse_args()
    collate(args.scenario)
