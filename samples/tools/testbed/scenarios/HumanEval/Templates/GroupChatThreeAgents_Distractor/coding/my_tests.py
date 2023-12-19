# Disable ruff linter for template files
# ruff: noqa: F821

__TEST__


def run_tests(candidate):
    check(candidate)
    # We can search for this string in the output
    print("ALL TESTS PASSED !#!#\nTERMINATE")
