"""
Unit test for retrieve_utils.py
"""
import os
import sys
import pytest

try:
    from autogen.agentchat.contrib.retriever.retrieve_utils import (
        split_text_to_chunks,
        extract_text_from_pdf,
        split_files_to_chunks,
        get_files_from_dir,
        is_url,
    )
    from autogen.agentchat.contrib.retriever import DEFAULT_RETRIEVER, get_retriever
    from autogen.token_count_utils import count_token

    Retriever = get_retriever(DEFAULT_RETRIEVER)
except ImportError:
    skip = True
else:
    skip = False

try:
    from unstructured.partition.auto import partition

    HAS_UNSTRUCTURED = True
except ImportError:
    HAS_UNSTRUCTURED = False

test_dir = os.path.join(os.path.dirname(__file__), "test_files")
expected_text = """AutoGen is an advanced tool designed to assist developers in harnessing the capabilities
of Large Language Models (LLMs) for various applications. The primary purpose of AutoGen is to automate and
simplify the process of building applications that leverage the power of LLMs, allowing for seamless
integration, testing, and deployment."""


@pytest.mark.skipif(skip, reason="dependency is not installed")
class TestRetrieveUtils:
    def test_split_text_to_chunks(self):
        long_text = "A" * 10000
        chunks = split_text_to_chunks(long_text, max_tokens=1000)
        assert all(count_token(chunk) <= 1000 for chunk in chunks)

    def test_split_text_to_chunks_raises_on_invalid_chunk_mode(self):
        with pytest.raises(AssertionError):
            split_text_to_chunks("A" * 10000, chunk_mode="bogus_chunk_mode")

    def test_extract_text_from_pdf(self):
        pdf_file_path = os.path.join(test_dir, "example.pdf")
        assert "".join(expected_text.split()) == "".join(extract_text_from_pdf(pdf_file_path).strip().split())

    def test_split_files_to_chunks(self):
        pdf_file_path = os.path.join(test_dir, "example.pdf")
        txt_file_path = os.path.join(test_dir, "example.txt")
        chunks = split_files_to_chunks([pdf_file_path, txt_file_path])
        assert all(
            isinstance(chunk, str) and "AutoGen is an advanced tool designed to assist developers" in chunk.strip()
            for chunk in chunks
        )

    def test_get_files_from_dir(self):
        files = get_files_from_dir(test_dir, recursive=False)
        assert all(os.path.isfile(file) for file in files)
        pdf_file_path = os.path.join(test_dir, "example.pdf")
        txt_file_path = os.path.join(test_dir, "example.txt")
        files = get_files_from_dir([pdf_file_path, txt_file_path])
        assert all(os.path.isfile(file) for file in files)
        files = get_files_from_dir(
            [
                pdf_file_path,
                txt_file_path,
                os.path.join(test_dir, "..", "..", "website/docs"),
                "https://raw.githubusercontent.com/microsoft/autogen/main/README.md",
            ],
            recursive=True,
        )
        assert all(os.path.isfile(file) for file in files)
        files = get_files_from_dir(
            [
                pdf_file_path,
                txt_file_path,
                os.path.join(test_dir, "..", "..", "website/docs"),
                "https://raw.githubusercontent.com/microsoft/autogen/main/README.md",
            ],
            recursive=True,
            types=["pdf", "txt"],
        )
        assert all(os.path.isfile(file) for file in files)
        assert len(files) == 3

    def test_is_url(self):
        assert is_url("https://www.example.com")
        assert not is_url("not_a_url")

    def test_custom_text_split_function(self):
        def custom_text_split_function(text):
            return [text[: len(text) // 2], text[len(text) // 2 :]]

        db_path = "/tmp/test_retrieve_utils"
        retriever = Retriever(
            path=db_path,
            name="mytestcollection",
            custom_text_split_function=custom_text_split_function,
            use_existing=False,
            recursive=False,
        )
        retriever.ingest_data(os.path.join(test_dir, "example.txt"))
        results = retriever.query(["autogen"], top_k=1)
        assert (
            "AutoGen is an advanced tool designed to assist developers in harnessing the capabilities"
            in results.get("documents")[0][0]
        )

    def test_retrieve_utils(self):
        retriever = Retriever(path="/tmp/chromadb", name="autogen-docs", use_existing=False)
        retriever.ingest_data("./website/docs")
        results = retriever.query(["autogen"], top_k=4, filter="AutoGen")

        print(results["ids"][0])
        assert len(results["ids"][0]) == 4

    @pytest.mark.skipif(
        not HAS_UNSTRUCTURED,
        reason="do not run if unstructured is not installed",
    )
    def test_unstructured(self):
        pdf_file_path = os.path.join(test_dir, "example.pdf")
        txt_file_path = os.path.join(test_dir, "example.txt")
        word_file_path = os.path.join(test_dir, "example.docx")
        chunks = split_files_to_chunks([pdf_file_path, txt_file_path, word_file_path])
        assert all(
            isinstance(chunk, str) and "AutoGen is an advanced tool designed to assist developers" in chunk.strip()
            for chunk in chunks
        )


if __name__ == "__main__":
    pytest.main()

    db_path = "/tmp/test_retrieve_utils_chromadb.db"
    if os.path.exists(db_path):
        os.remove(db_path)  # Delete the database file after tests are finished
