import os
import sys
from autogenbench.tabulate_cmd import default_tabulate, default_scorer


def scorer(instance_dir, success_strings=["FINAL SCORE: 1"]):
    return default_scorer(instance_dir, success_strings=success_strings)


def main(args):
    default_tabulate(args, scorer=scorer)


if __name__ == "__main__" and __package__ is None:
    main(sys.argv)
