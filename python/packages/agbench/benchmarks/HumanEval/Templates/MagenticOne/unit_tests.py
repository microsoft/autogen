# Disable ruff linter for template files
# ruff: noqa: F821 E722
import sys


__TEST__


def run_tests(candidate):
    try:
        check(candidate)
        # We can search for this string in the output
        print("ALL TESTS PASSED !#!#")
    except AssertionError:
        sys.exit("SOME TESTS FAILED - TRY AGAIN !#!#")
