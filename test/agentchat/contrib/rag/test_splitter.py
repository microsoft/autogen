import os
import unittest
from unittest.mock import patch
from autogen.agentchat.contrib.rag.splitter import Splitter, TextLineSplitter

# get the path of current file
here = os.path.abspath(os.path.dirname(__file__))


class TestSplitter(unittest.TestCase):
    def test_get_files_from_dir(self):
        # Test when dir_path is a directory
        dir_path = os.path.join(here, "test_files")
        expected_files = [
            os.path.join(here, "test_files", "example.txt"),
            os.path.join(here, "test_files", "example.pdf"),
        ]
        files = Splitter.get_files_from_dir(dir_path)
        self.assertEqual(files, expected_files)

        # Test when dir_path is a file
        dir_path = os.path.join(here, "test_files", "example.txt")
        expected_files = [os.path.join(here, "test_files", "example.txt")]
        files = Splitter.get_files_from_dir(dir_path)
        self.assertEqual(files, expected_files)

        # Test when dir_path is a URL
        dir_path = "https://raw.githubusercontent.com/microsoft/autogen/main/README.md"
        expected_files = [os.path.join(here, "tmp/download/README.md")]
        with patch(
            "autogen.agentchat.contrib.rag.splitter.Splitter.get_file_from_url",
            return_value=os.path.join(here, "tmp/download/README.md"),
        ):
            files = Splitter.get_files_from_dir(dir_path)
            self.assertEqual(files, expected_files)

    def test_get_file_from_url(self):
        url = "https://raw.githubusercontent.com/microsoft/autogen/main/README.md"
        save_path = "./tmp/download/README.md"
        with patch("requests.get"):
            returned_save_path = Splitter.get_file_from_url(url, save_path)
            self.assertEqual(returned_save_path, save_path)

    def test_is_url(self):
        # Test when string is a valid URL
        string = "https://example.com"
        self.assertTrue(Splitter.is_url(string))

        # Test when string is not a valid URL
        string = "example.com"
        self.assertFalse(Splitter.is_url(string))


class TestTextLineSplitter(unittest.TestCase):
    def test_split_text_to_chunks(self):
        text = "This is a long text that needs to be split into chunks."
        chunk_size = 10
        chunk_mode = "multi_lines"
        must_break_at_empty_line = True
        overlap = 1
        expected_chunks = ["This ", "is a ", "long text that needs to be split into chunks."]
        splitter = TextLineSplitter(docs_path="", recursive=True)
        chunks = splitter.split_text_to_chunks(text, chunk_size, chunk_mode, must_break_at_empty_line, overlap)
        self.assertEqual(chunks, expected_chunks)


if __name__ == "__main__":
    unittest.main()
