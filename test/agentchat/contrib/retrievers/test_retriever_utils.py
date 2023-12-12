from pathlib import Path
from autogen.agentchat.contrib.retriever.retrieve_utils import (
    split_text_to_chunks,
    split_files_to_chunks,
    get_file_from_url,
    get_files_from_dir,
    is_url,
)

test_dir = Path(__file__).parent.parent.parent.parent / "test_files"


def test_split_text_to_chunks():
    text = "Hello, World! This is a test of the split_text_to_chunks() function."
    chunks = split_text_to_chunks(text)
    assert len(chunks) == 1
    chunks = split_text_to_chunks(text, max_tokens=10)
    assert len(chunks) == 2


def test_split_files_to_chunks():
    files = [test_dir / "example.txt"]
    chunks = split_files_to_chunks(files)
    assert len(chunks) == 1
    chunks = split_files_to_chunks(files, max_tokens=50)
    assert len(chunks) == 2


def test_get_files_from_dir():
    files = get_files_from_dir(str(test_dir))
    assert len(files) == 8


def test_is_url():
    assert is_url("https://google.com")
    assert not is_url("google")


def test_get_file_from_url():
    file = get_file_from_url("https://google.com")
    assert file is not None
