import unittest
from unittest.mock import patch, MagicMock, call
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

from autogen.browser_utils.headless_chrome_browser import HeadlessChromeBrowser


class TestHeadlessChromeBrowser(unittest.TestCase):
    @patch.object(WebDriver, "get")
    def test_set_address(self, mock_get):
        # Arrange
        browser = HeadlessChromeBrowser()

        # Act
        browser.set_address("https://www.example.com")

        # Assert
        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(mock_get.call_args_list[0], call("about:blank"))
        self.assertEqual(mock_get.call_args_list[1], call("https://www.example.com"))

    @patch.object(WebDriver, "execute_script")
    def test_page_content(self, mock_execute_script):
        # Arrange
        mock_execute_script.return_value = "<html><body><p>Hello, World!</p></body></html>"
        browser = HeadlessChromeBrowser()
        browser.visit_page("https://www.example.com")
        # Act
        content = browser.page_content

        # Assert
        self.assertEqual("Hello, World!", content)

    @patch.object(WebDriver, "get")
    @patch.object(WebDriver, "find_element")
    def test_bing_search(self, mock_find_element, mock_get):
        # Arrange
        mock_element = MagicMock()
        mock_element.submit = MagicMock()
        mock_element.clear = MagicMock()
        mock_element.send_keys = MagicMock()
        mock_find_element.return_value = mock_element
        browser = HeadlessChromeBrowser()

        # Act
        browser._bing_search("test query")

        # Assert
        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(mock_get.call_args_list[0], call("about:blank"))
        self.assertEqual(mock_get.call_args_list[1], call("https://www.bing.com"))
        mock_find_element.assert_called_once_with(By.NAME, "q")
        mock_element.clear.assert_called_once()
        mock_element.send_keys.assert_called_once_with("test query")
        mock_element.submit.assert_called_once()

    def test_page_up(self):
        # Arrange
        browser = HeadlessChromeBrowser()
        browser._set_page_content("Hello, World!" * 1000)  # Set a long page content
        browser.viewport_current_page = 1  # Set the current page to 1

        # Act
        browser.page_up()

        # Assert
        self.assertEqual(browser.viewport_current_page, 0)  # The current page should now be 0

    def test_page_down(self):
        # Arrange
        browser = HeadlessChromeBrowser()
        browser._set_page_content("Hello, World!" * 1000)  # Set a long page content
        browser.viewport_current_page = 1  # Set the current page to 0

        # Act
        browser.page_down()

        # Assert
        self.assertEqual(browser.viewport_current_page, 1)  # The current page should now be 1

    @patch.object(WebDriver, "get")
    @patch.object(WebDriver, "execute_script")
    def test_visit_page(self, mock_execute_script, mock_get):
        # Arrange
        mock_execute_script.return_value = "<html><body><p>Hello, World!</p></body></html>"
        browser = HeadlessChromeBrowser()

        # Act
        browser.visit_page("https://www.example.com")

        # Assert
        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(mock_get.call_args_list[0], call("about:blank"))
        self.assertEqual(mock_get.call_args_list[1], call("https://www.example.com"))
        self.assertEqual(browser.page_content, "Hello, World!")


if __name__ == "__main__":
    unittest.main()
