import os
import sys
import argparse
import csv


def metrics(results_fh):
    """
    Compute metrics from collated GAIA results.

    Args:
        results_fh (File Stream): A file stream containing the collated results in CSV.
    """

    reader = csv.reader(results_fh)
    first_row = next(reader)  # Read the first line

    num_trials = len(first_row) - 1  # Don't count the first column (TestId)

    # Set up the counters
    counters = []
    for i in range(0, num_trials):
        counters.append({"successes": 0, "failures": 0, "missing": 0})

    # Load the results. We'll need to iterate over them a few times.
    results = list()
    for row in reader:
        name = row[0]
        trials = [(None if v.strip() == "" else int(v)) for v in row[1:]]
        for i in range(0, len(trials)):
            v = trials[i]
            if v is None:
                counters[i]["missing"] += 1
            elif v > 0:
                counters[i]["successes"] += 1
            else:
                counters[i]["failures"] += 1

        results.append([name, trials])

    def _safe_div(num, denom):
        if denom == 0:
            return ""
        else:
            return num / denom

    # Print the header
    for i in range(0, len(counters)):
        counter = counters[i]
        n = counter["successes"] + counter["failures"] + counter["missing"]
        score = _safe_div(counter["successes"], n)
        print(f"{i},{n},{counter['successes']},{counter['failures']},{counter['missing']},{score}")


###############################################################################
if __name__ == "__main__":
    script_path = os.path.realpath(__file__)
    script_name = os.path.basename(script_path)
    script_dir = os.path.dirname(script_path)

    parser = argparse.ArgumentParser(
        description=f"""
{script_name} will compute metrics on the collated results of the GAIA scenarios. Use collate_gaia.py to prepare input to this script.

The output will be formatted as a CSV with the following schema:

Trial,  n,      successes,  failures,   missing,    score
0       N_0,    s_0         f_0         m_0,        p_0
0       N_1,    s_1         f_1         m_1,        p_1
...
M       N_M,    s_M         f_M         m_M,        p_M

Where:

    N_i is the number of questions in trial i
    s_i is the number of successes in trial i
    f_i is the number of failures in trial i
    m_i is the number of missing values in trial i
    p_i is the proportion of successes in trail i (i.e, s_i / N_i)

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
