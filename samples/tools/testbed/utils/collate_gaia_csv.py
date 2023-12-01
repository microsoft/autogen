import os
import json
import re
import sys
import argparse


def normalize_answer(a):
    # Lower case
    # Trim (left and right)
    # Replace multiple spaces with one space
    # Remove trailing punctuation
    return re.sub(r"[\.\!\?]+$", "", re.sub(r"\s+", " ", a.strip().lower()))


def collate(results_dir):
    """
    Collate the results of running GAIA

    Args:
        results_dir (path): The folder were results were be saved.
    """

    all_results = list()
    max_instances = 0

    for test_id in os.listdir(results_dir):
        test_path = os.path.join(results_dir, test_id)

        # Collect the reslts vector
        results = [test_id]

        instance = 0
        instance_dir = os.path.join(test_path, str(instance))
        while os.path.isdir(instance_dir):
            expected_answer_file = os.path.join(instance_dir, "expected_answer.txt")
            if not os.path.isfile(expected_answer_file):
                # Expected ansewr is missing
                results.append("")

                instance += 1
                instance_dir = os.path.join(test_path, str(instance))
                continue

            expected_answer = "!!!NULL ANSWER!!!"
            with open(expected_answer_file, "rt") as fh:
                expected_answer = fh.read().strip()

            console_log_file = os.path.join(instance_dir, "console_log.txt")
            if not os.path.isfile(console_log_file):
                # Console log file missing
                results.append("")

                instance += 1
                instance_dir = os.path.join(test_path, str(instance))
                continue

            with open(console_log_file, "rt") as fh:
                console_log = fh.read()

                final_answer = ""
                m = re.search(r"FINAL ANSWER:(.*?)\n", console_log, re.DOTALL)
                if m:
                    final_answer = m.group(1).strip()

                # print(f"Expected Answer: {expected_answer}\nAutogen Answer: {final_answer}\n")

                if normalize_answer(expected_answer) == normalize_answer(final_answer):
                    results.append("1")
                else:
                    results.append("-1")

            instance += 1
            instance_dir = os.path.join(test_path, str(instance))

        max_instances = max(max_instances, instance)

        # Buffer the results
        all_results.append(results)

    # Create a header
    header = "TestId"
    for i in range(0, max_instances):
        header += ",Trial" + str(i)
    print(header)

    # Print a fully-populated table of results
    for r in all_results:
        while len(r) < max_instances + 1:
            r.append("")
        print(",".join(r))


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
{script_name} will collate the results of the GAIA scenarios and output them to a CSV. The CSV format is as follows:

TestId,      Trial0, Trial1, ...,    TrialN
uuid_1,      x_10,   x_11,   ...,    X_1N
uuid_2,      x_20,   x_21,   ...,    X_2N
...
uuid_M,      x_M0,   x_M1,   ...,    X_MN

Where uuid_i is the identifier of the ith test question, and x_ij is 1 or -1 depending on if the test passed or failed, respectively. If data for the trial is missing (e.g., due to a runtime error, the value will be an empty string "".
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
