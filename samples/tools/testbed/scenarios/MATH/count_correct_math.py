import argparse
import json
import os


def main(args):
    stars = "*" * 100

    # initiate the correct count for each trial
    correct_count = [0 for i in range(args.num_trials)]

    for i in range(args.num_trials):
        for problem_name in os.listdir(args.path):
            problem_path = os.path.join(args.path, problem_name, str(i))
            if os.path.isdir(problem_path):
                checker_file_path = os.path.join(problem_path, "checker_messages.json")

                with open(checker_file_path, "r") as file:
                    checker_messages = json.load(file)

                    check_result = checker_messages["checker_proxy"][-1]["content"].lower()

                    if (
                        "the answer is correct" in check_result
                        or "the answer is approximated but should be correct" in check_result
                    ):
                        correct_count[i] += 1
                        # print(f"{problem_name} | Correct")
                    # else:
                    # print(f"{problem_name} | Wrong")

        print(f"{stars}\nTrial {i} | Total Correct: {correct_count[i]} | Total Problems: {len(os.listdir(args.path))}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""Print Math Problems results.""".strip(),
    )
    parser.add_argument(
        "--path",
        "-p",
        type=str,
        default="./results/problems/",
        help="Path to the problems directory",
    )
    # num trials
    parser.add_argument(
        "--num_trials",
        "-n",
        type=int,
        default=1,
        help="Number of trials to check",
    )

    args = parser.parse_args()
    main(args)
