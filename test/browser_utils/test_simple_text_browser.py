import os
import tempfile
import unittest
from unittest.mock import patch, Mock

import requests

from autogen.browser_utils.simple_text_browser import SimpleTextBrowser


class TestSimpleTextBrowser(unittest.TestCase):
    def setUp(self):
        self.browser = SimpleTextBrowser()

    def test_init(self):
        self.assertEqual(self.browser.start_page, "about:blank")
        self.assertEqual(self.browser.viewport_size, 1024 * 8)
        self.assertIsNone(self.browser.downloads_folder)
        self.assertIsNone(self.browser.bing_api_key)
        self.assertIsNone(self.browser.request_kwargs)

    def test_set_address(self):
        self.browser.set_address("https://www.example.com")
        self.assertEqual(self.browser.address, "https://www.example.com")

    def test_viewport(self):
        self.browser.set_address("https://www.example.com")
        self.assertIsInstance(self.browser.viewport, str)

    def test_page_content(self):
        self.browser.set_address("https://www.example.com")
        self.assertIsInstance(self.browser.page_content, str)

    def test_page_down(self):
        self.browser.set_address("https://www.example.com")
        current_page = self.browser.viewport_current_page
        self.browser.page_down()
        self.assertEqual(
            self.browser.viewport_current_page, min(current_page + 1, len(self.browser.viewport_pages) - 1)
        )

    def test_page_up(self):
        self.browser.set_address("https://www.example.com")
        self.browser.page_down()
        current_page = self.browser.viewport_current_page
        self.browser.page_up()
        self.assertEqual(self.browser.viewport_current_page, max(current_page - 1, 0))

    def test_visit_page(self):
        content = self.browser.visit_page("https://www.example.com")
        self.assertIsInstance(content, str)

    @patch.object(requests, "get")
    def test_bing_api_call(self, mock_get):
        # Arrange
        mock_response = Mock()
        expected_result = {"webPages": {"value": []}}
        mock_response.json.return_value = expected_result
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        self.browser.bing_api_key = "test_key"

        # Act
        result = self.browser._bing_api_call("test_query")

        # Assert
        mock_get.assert_called_once_with(
            "https://api.bing.microsoft.com/v7.0/search",
            headers={"Ocp-Apim-Subscription-Key": "test_key"},
            params={"q": "test_query", "textDecorations": False, "textFormat": "raw"},
            stream=False,
        )
        self.assertEqual(result, expected_result)

    @patch.object(SimpleTextBrowser, "_bing_api_call")
    def test_bing_search(self, mock_bing_api_call):
        # Arrange
        expected_result = {
            "webPages": {"value": [{"name": "Test Page", "url": "https://www.example.com", "snippet": "Test Snippet"}]}
        }
        mock_bing_api_call.return_value = expected_result
        query = "test_query"

        # Act
        self.browser._bing_search(query)

        # Assert
        mock_bing_api_call.assert_called_once_with(query)
        self.assertIn("Test Page", self.browser.page_content)
        self.assertIn("https://www.example.com", self.browser.page_content)
        self.assertIn("Test Snippet", self.browser.page_content)

    @patch.object(requests, "get")
    def test_fetch_page_text_plain(self, mock_get):
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.iter_content.return_value = iter([b"Test content".decode("utf-8")])  # decode bytes to string
        mock_get.return_value = mock_response
        url = "https://www.example.com/test.txt"

        # Act
        self.browser.set_address(url)

        # Assert
        mock_get.assert_called_once_with(url, stream=True)
        self.assertEqual(self.browser.page_content, "Test content")  # compare with decoded string

    @patch.object(requests, "get")
    def test_downloads_folder(self, mock_get):
        # Arrange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/octet-stream"}
        mock_response.iter_content.return_value = iter([b"Download content"])
        mock_get.return_value = mock_response
        url = "https://www.example.com/test.bin"

        with tempfile.TemporaryDirectory() as downloads_folder:
            self.browser.downloads_folder = downloads_folder

            # Act
            self.browser.set_address(url)

            # Assert
            mock_get.assert_called_once_with(url, stream=True)
            download_path = os.path.join(downloads_folder, os.listdir(downloads_folder)[0])
            with open(download_path, "rb") as f:
                content = f.read()
            self.assertEqual(content, b"Download content")
            self.assertIn("Downloaded", self.browser.page_content)
            self.assertIn(url, self.browser.page_content)
            self.assertIn(download_path, self.browser.page_content)


if __name__ == "__main__":
    unittest.main()
