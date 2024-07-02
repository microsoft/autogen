import os
import sys

from agbench.tabulate_cmd import default_tabulate


def main(args):
    default_tabulate(args)


if __name__ == "__main__" and __package__ is None:
    main(sys.argv)
