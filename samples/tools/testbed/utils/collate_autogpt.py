import argparse
import os
import re
import subprocess
import sys


def collate(results_dir="results"):
    """
    Collate the results of running AutoGPT test.

    Args:
        results_dir (str, optional): The folder where results are saved. Defaults to "results".
    """

    all_results = list()
    max_instances = 0

    for test_name in os.listdir(results_dir):
        test_path = os.path.join(results_dir, test_name)

        # Collect the results vector
        results = [test_name]

        instance = 0
        instance_dir = os.path.join(test_path, str(instance))
        while os.path.isdir(instance_dir):
            console_log = os.path.join(instance_dir, "console_log.txt")
            if os.path.isfile(console_log):
                with open(console_log, "rt") as fh:
                    content = fh.read()
                    if "ALL TESTS PASSED!" in content:
                        # Ideally we would have a more distinctive pattern.
                        results.append(str(len(re.findall(r"\n(.*?) \(to (.*?)\)\:\n", content))))
                    else:
                        # Sometimes the task actually succeeds, but the check.py isn't properly called
                        result = subprocess.run(
                            [sys.executable, "../check.py"],
                            cwd=os.path.join(instance_dir, "coding"),
                            capture_output=True,
                            text=True,
                        )
                        if "error" in result.stderr or result.returncode != 0:
                            results.append("-1")
                        else:
                            # The task actually succeeds.
                            if "ALL TESTS PASSED!" in result.stdout:
                                results.append(str(len(re.findall(r"\n(.*?) \(to (.*?)\)\:\n", content))))
                            else:
                                results.append("-1")
            else:
                # Missing results will appear as blanks
                results.append("")

            instance += 1
            instance_dir = os.path.join(test_path, str(instance))

        max_instances = max(max_instances, instance)

        # Buffer the results
        all_results.append(results)

    # Create a header
    header = "TestName"
    for i in range(0, max_instances):
        header += ",Trial" + str(i)
    print(header)

    # Print a fully-populated table of results
    for r in all_results:
        while len(r) < max_instances + 1:
            r.append("")
        print(",".join(r))


if __name__ == "__main__":
    script_path = os.path.realpath(__file__)
    script_name = os.path.basename(script_path)
    script_dir = os.path.dirname(script_path)

    # Path to the default results directory
    # (relative to this script, up on directory, then into the results folder)
    default_results_dir = os.path.realpath(os.path.join(script_dir, os.path.pardir, "results"))

    parser = argparse.ArgumentParser(
        description=f"""
{script_name} will collate the results of the AutoGPT scenarios and output them to a CSV. The CSV format is as follows:

TestName,      Trial0, Trial1, ...,    TrialN
Test_1, x_10,   x_11,   ...,    X_1N
Test_2, x_20,   x_21,   ...,    X_2N
...
Test_M, x_M0,   x_M1,   ...,    X_MN


Where x_ij is the number of AssistantAgent conversation turns needed to pass all the tests for problem i, in Trial/repetition j. If the agent was not able to pass the tests by the end of the conversation, the value will be -1. If data for the trial is missing, the value will be an empty string "".
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
