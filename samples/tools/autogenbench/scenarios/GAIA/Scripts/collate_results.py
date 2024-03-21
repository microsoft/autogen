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


def collate(results_dir):
    """
    Collate the results of running GAIA. Print the results in the format accepted by the leaderboard.

    Args:
        results_dir (path): The folder where results were be saved.
    """

    for test_id in os.listdir(results_dir):
        test_path = os.path.join(results_dir, test_id)

        for instance in os.listdir(test_path):
            instance_dir = os.path.join(test_path, str(instance))
            console_log_file = os.path.join(instance_dir, "console_log.txt")

            final_answer = ""
            console_log = ""
            if os.path.isfile(console_log_file):
                with open(console_log_file, "rt") as fh:
                    console_log = fh.read()

                    # Trim the console log
                    m = re.search(
                        r"SCENARIO.PY STARTING !#!#(.*)", console_log, re.DOTALL
                    )
                    if m:
                        console_log = m.group(1).strip()

                    # Extract the final answer
                    final_answer = ""
                    m = re.search(r"FINAL ANSWER:(.*?)\n", console_log, re.DOTALL)
                    if m:
                        final_answer = m.group(1).strip()

            expected_answer_file = os.path.join(instance_dir, "expected_answer.txt")
            expected_answer = "NOT PROVIDED !#!#"
            if os.path.isfile(expected_answer_file):
                with open(expected_answer_file, "rt") as fh:
                    expected_answer = fh.read().strip()

            prompt_file = os.path.join(instance_dir, "prompt.txt")
            prompt = None
            if os.path.isfile(prompt_file):
                with open(prompt_file, "rt") as fh:
                    prompt = fh.read().strip()

            # Apply approximate string matching
            is_correct = normalize_answer(final_answer) == normalize_answer(expected_answer)

            # Parse the steps
            steps = [s.strip() for s in re.split(r"\-\-\-\-\-\-\-\-+", console_log) if len(s) > 0]

            print(
                json.dumps(
                    {
                        "task_id": test_id,
                        "trial": instance,
                        "question": prompt,
                        "is_correct": is_correct,
                        "model_answer": final_answer,
                        "expected_answer": expected_answer,
                        "reasoning_trace": steps,
                    },
                    indent=4,
                )
            )


###############################################################################
if __name__ == "__main__":
    script_path = os.path.realpath(__file__)
    script_name = os.path.basename(script_path)
    script_dir = os.path.dirname(script_path)

    parser = argparse.ArgumentParser(
        description=f"""
{script_name} will collate the results of the GAIA scenarios into the jsonl format that can be submit to AgentEval.
""".strip(),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "scenario",
        help="Path to the scenario results.",
    )
    args = parser.parse_args()
    collate(args.scenario)
