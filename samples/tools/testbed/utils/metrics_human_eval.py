import os
import sys
import argparse
import csv


def metrics(results_fh):
    """
    Compute metrics from collated HumanEval results.

    Args:
        results_fh (File Stream): A file stream containing the collated results in CSV.
    """

    reader = csv.reader(results_fh)
    first_row = next(reader)  # Read the first line

    num_trials = len(first_row) - 1  # Don't count the first column (TestId)
    max_turns = 0
    num_rows = 0

    # Load the results. We'll need to iterate over them a few times.
    results = list()
    for row in reader:
        num_rows += 1

        name = row[0]
        trials = [(None if v.strip() == "" else int(v)) for v in row[1:]]
        for v in trials:
            if v is not None:
                max_turns = max(max_turns, v)
        results.append([name, trials])

    # Print the header
    header = ["Trial"]
    for i in range(1, max_turns + 1):
        header.append("cumulative_passes_by_turn_" + str(i))
    header.append("fails")
    header.append("missing")
    print(",".join(header))

    # Compute the metrics
    def _metrics_for_trial(t):
        counts = [None]
        fails = 0
        missing = 0

        # Compute cumulative passes for each conversation turn
        for i in range(1, max_turns + 1):
            counts.append(0)
            assert len(counts) == i + 1

            for r in results:
                v = r[1][t]
                if v is not None:
                    v = int(v)
                    if 0 <= v and v <= i:
                        counts[i] += 1

        # Count missing and failed
        for r in results:
            v = r[1][t]
            if v is None:
                missing += 1
            elif int(v) < 0:
                fails += 1

        # Prepare the row in the format specified by the header
        return str(t) + "," + ",".join([str(v) for v in counts[1:]]) + "," + str(fails) + "," + str(missing)

    # Print each row
    for t in range(0, num_trials):
        print(_metrics_for_trial(t))


###############################################################################
if __name__ == "__main__":
    script_path = os.path.realpath(__file__)
    script_name = os.path.basename(script_path)
    script_dir = os.path.dirname(script_path)

    parser = argparse.ArgumentParser(
        description=f"""
{script_name} will compute metrics on the collated results of the HumanEval scenarios. Use collate_human_eval.py to prepare input to this script.

The output will be formatted as a CSV with the following schema:

Trial, cumulative_passes_by_turn_1, ..., cumulative_passes_by_turn_N, fails, missing
0      x_01,                             x_0N,                        y_0,   z_0
1      x_11,                             x_1N,                        y_1,   z_1
...
M      x_M1,                             x_MN,                        y_M,   z_M

Where:

  x_ij is the number of HumanEval problems in Trial i that achieved a passing result by conversation turn j.
  y_i  is the number of HumanEval problems in Trial i that never achieved a passing result (they failed).
  z_i  is the number of HumanEval problems in Trial i that have missing data.

""".strip(),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "scenario",
        nargs="?",
        help="Path to collated results. If '-' or omitted, read from stdin. (default: '-')",
        default="-",
    )
    args = parser.parse_args()

    if args.scenario == "" or args.scenario == "-":
        metrics(sys.stdin)
    else:
        with open(args.scenario, "rt") as fh:
            metrics(fh)
