# Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
#
# SPDX-License-Identifier: Apache-2.0
#
# Portions derived from  https://github.com/microsoft/autogen are under the MIT License.
# SPDX-License-Identifier: MIT
import os
import sys

from autogenbench.tabulate_cmd import default_tabulate


def main(args):
    default_tabulate(args)


if __name__ == "__main__" and __package__ is None:
    main(sys.argv)
