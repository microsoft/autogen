#!/usr/bin/env python3 -m pytest

import hashlib
import math
import os
import pathlib
import re

import pytest
import requests
from autogen_magentic_one.markdown_browser import BingMarkdownSearch, RequestsMarkdownBrowser

BLOG_POST_URL = "https://microsoft.github.io/autogen/0.2/blog/2023/04/21/LLM-tuning-math"
BLOG_POST_TITLE = "Does Model and Inference Parameter Matter in LLM Applications? - A Case Study for MATH | AutoGen 0.2"
BLOG_POST_STRING = "Large language models (LLMs) are powerful tools that can generate natural language texts for various applications, such as chatbots, summarization, translation, and more. GPT-4 is currently the state of the art LLM in the world. Is model selection irrelevant? What about inference parameters?"
BLOG_POST_FIND_ON_PAGE_QUERY = "an example where high * complex"
BLOG_POST_FIND_ON_PAGE_MATCH = "an example where high cost can easily prevent a generic complex"

WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/Microsoft"
WIKIPEDIA_TITLE = "Microsoft"
WIKIPEDIA_STRING = "Redmond"

PLAIN_TEXT_URL = "https://raw.githubusercontent.com/microsoft/autogen/main/README.md"

DOWNLOAD_URL = "https://arxiv.org/src/2308.08155"

PDF_URL = "https://arxiv.org/pdf/2308.08155.pdf"
PDF_STRING = "Figure 1: AutoGen enables diverse LLM-based applications using multi-agent conversations."

DIR_TEST_STRINGS = [
    "# Index of ",
    "[.. (parent directory)]",
    "/python/packages/autogen-magentic-one/tests/browser_utils",
]

LOCAL_FILE_TEST_STRINGS = [
    BLOG_POST_STRING,
    BLOG_POST_FIND_ON_PAGE_MATCH,
]


skip_all = False


def _rm_folder(path: str) -> None:
    """Remove all the regular files in a folder, then deletes the folder. Assumes a flat file structure, with no subdirectories."""
    for fname in os.listdir(path):
        fpath = os.path.join(path, fname)
        if os.path.isfile(fpath):
            os.unlink(fpath)
    os.rmdir(path)


def normalize_text(text: str) -> str:
    text = "\n".join([line.rstrip() for line in re.split(r"\r?\n", text)])
    return re.sub(r"\n{3,}", "\n\n", text)


@pytest.mark.skipif(
    skip_all,
    reason="do not run if dependency is not installed",
)
def test_requests_markdown_browser() -> None:
    # Create a downloads folder (removing any leftover ones from prior tests)
    downloads_folder = os.path.join(os.getcwd(), "downloads")
    if os.path.isdir(downloads_folder):
        _rm_folder(downloads_folder)
    os.mkdir(downloads_folder)

    # Instantiate the browser
    viewport_size = 1024
    browser = RequestsMarkdownBrowser(
        viewport_size=viewport_size,
        downloads_folder=downloads_folder,
        search_engine=BingMarkdownSearch(),
    )

    # Test that we can visit a page and find what we expect there
    top_viewport = browser.visit_page(BLOG_POST_URL)
    assert browser.viewport == top_viewport
    assert browser.page_title is not None
    assert browser.page_title.strip() == BLOG_POST_TITLE.strip()
    page_content = browser.page_content.replace("\\", "")
    assert BLOG_POST_STRING in page_content

    # Check if page splitting works
    approx_pages = math.ceil(len(browser.page_content) / viewport_size)  # May be fewer, since it aligns to word breaks
    assert len(browser.viewport_pages) <= approx_pages
    assert abs(len(browser.viewport_pages) - approx_pages) <= 1  # allow only a small deviation
    assert browser.viewport_pages[0][0] == 0
    assert browser.viewport_pages[-1][1] == len(browser.page_content)

    # Make sure we can reconstruct the full contents from the split pages
    buffer = ""
    for bounds in browser.viewport_pages:
        buffer += browser.page_content[bounds[0] : bounds[1]]
    assert buffer == browser.page_content

    # Test scrolling (scroll all the way to the bottom)
    for i in range(1, len(browser.viewport_pages)):
        browser.page_down()
        assert browser.viewport_current_page == i
    # Test scrolloing beyond the limits
    for _ in range(0, 5):
        browser.page_down()
        assert browser.viewport_current_page == len(browser.viewport_pages) - 1

    # Test scrolling (scroll all the way to the bottom)
    for i in range(len(browser.viewport_pages) - 2, 0, -1):
        browser.page_up()
        assert browser.viewport_current_page == i
    # Test scrolloing beyond the limits
    for _ in range(0, 5):
        browser.page_up()
        assert browser.viewport_current_page == 0

    # Test Wikipedia handling
    assert WIKIPEDIA_STRING in browser.visit_page(WIKIPEDIA_URL)
    assert WIKIPEDIA_TITLE.strip() == browser.page_title.strip()

    # Visit a plain-text file
    response = requests.get(PLAIN_TEXT_URL)
    response.raise_for_status()
    expected_results = re.sub(r"\s+", " ", string=response.text, flags=re.DOTALL).strip()
    # Run the normalize code that the markdown request module uses
    expected_results = normalize_text(expected_results)

    browser.visit_page(PLAIN_TEXT_URL)
    assert re.sub(r"\s+", " ", string=browser.page_content, flags=re.DOTALL).strip() == expected_results

    # Disrectly download a ZIP file and compute its sha256
    response = requests.get(DOWNLOAD_URL, stream=True)
    response.raise_for_status()
    expected_sha256 = hashlib.sha256(response.raw.read()).hexdigest()

    # Download it with the browser and check for a match
    viewport = browser.visit_page(DOWNLOAD_URL)
    m = re.search(r"Saved file to '(.*?)'", viewport)
    assert m is not None
    download_loc = m.group(1)
    with open(download_loc, "rb") as fh:
        downloaded_sha256 = hashlib.sha256(fh.read()).hexdigest()

    # MD%s should match
    assert expected_sha256 == downloaded_sha256

    # Fetch a PDF
    viewport = browser.visit_page(PDF_URL)
    assert PDF_STRING in viewport

    # Test find in page
    browser.visit_page(BLOG_POST_URL)
    find_viewport = browser.find_on_page(BLOG_POST_FIND_ON_PAGE_QUERY)
    assert find_viewport is not None
    assert BLOG_POST_FIND_ON_PAGE_MATCH in find_viewport
    assert find_viewport is not None

    loc = browser.viewport_current_page
    find_viewport = browser.find_on_page("LLM app*")
    assert find_viewport is not None

    # Find next using the same query
    for _ in range(0, 10):
        find_viewport = browser.find_on_page("LLM app*")
        assert find_viewport is not None

        new_loc = browser.viewport_current_page
        assert new_loc != loc
        loc = new_loc

    # Find next using find_next
    for _ in range(0, 10):
        find_viewport = browser.find_next()
        assert find_viewport is not None

        new_loc = browser.viewport_current_page
        assert new_loc != loc
        loc = new_loc

    # Bounce around
    browser.viewport_current_page = 0
    find_viewport = browser.find_on_page("For Further Reading")
    assert find_viewport is not None
    loc = browser.viewport_current_page

    browser.page_up()
    assert browser.viewport_current_page != loc
    find_viewport = browser.find_on_page("For Further Reading")
    assert find_viewport is not None
    assert loc == browser.viewport_current_page

    # Find something that doesn't exist
    find_viewport = browser.find_on_page("7c748f9a-8dce-461f-a092-4e8d29913f2d")
    assert find_viewport is None
    assert loc == browser.viewport_current_page  # We didn't move

    # Clean up
    _rm_folder(downloads_folder)


@pytest.mark.skipif(
    skip_all,
    reason="do not run if dependency is not installed",
)
def test_local_file_browsing() -> None:
    directory = os.path.dirname(__file__)
    test_file = os.path.join(directory, "test_files", "test_blog.html")
    browser = RequestsMarkdownBrowser()

    # Directory listing via open_local_file
    viewport = browser.open_local_file(directory)
    for target_string in DIR_TEST_STRINGS:
        viewport = viewport.replace("\\", "")
        assert target_string in viewport

    # Directory listing via file URI
    viewport = browser.visit_page(pathlib.Path(os.path.abspath(directory)).as_uri())
    for target_string in DIR_TEST_STRINGS:
        viewport = viewport.replace("\\", "")
        assert target_string in viewport

    # File access via file open_local_file
    browser.open_local_file(test_file)
    for target_string in LOCAL_FILE_TEST_STRINGS:
        page_content = browser.page_content.replace("\\", "")
        assert target_string in page_content

    # File access via file URI
    browser.visit_page(pathlib.Path(os.path.abspath(test_file)).as_uri())
    for target_string in LOCAL_FILE_TEST_STRINGS:
        page_content = browser.page_content.replace("\\", "")
        assert target_string in page_content


if __name__ == "__main__":
    """Runs this file's tests from the command line."""
    test_requests_markdown_browser()
    test_local_file_browsing()
