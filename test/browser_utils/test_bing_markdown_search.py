#!/usr/bin/env python3 -m pytest
import os

import pytest

try:
    from autogen.browser_utils import BingMarkdownSearch
except ImportError:
    skip_all = True
else:
    skip_all = False

bing_api_key = None
if "BING_API_KEY" in os.environ:
    bing_api_key = os.environ["BING_API_KEY"]
    del os.environ["BING_API_KEY"]
skip_api = bing_api_key is None

BING_QUERY = "Microsoft wikipedia"
BING_STRING = f"A Bing search for '{BING_QUERY}' found"
BING_EXPECTED_RESULT = "https://en.wikipedia.org/wiki/Microsoft"


@pytest.mark.skipif(
    skip_all,
    reason="do not run if dependency is not installed",
)
def test_bing_markdown_search():
    search_engine = BingMarkdownSearch()
    results = search_engine.search(BING_QUERY)
    assert BING_STRING in results
    assert BING_EXPECTED_RESULT in results


@pytest.mark.skipif(
    skip_api,
    reason="skipping tests that require a Bing API key",
)
def test_bing_markdown_search_api():
    search_engine = BingMarkdownSearch(bing_api_key=bing_api_key)
    results = search_engine.search(BING_QUERY)
    assert BING_STRING in results
    assert BING_EXPECTED_RESULT in results


if __name__ == "__main__":
    """Runs this file's tests from the command line."""
    test_bing_markdown_search()
    test_bing_markdown_search_api()
