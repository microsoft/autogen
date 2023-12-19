import base64
import os
import pdb
import unittest
from unittest.mock import patch

import pytest
import requests

try:
    from PIL import Image

    from autogen.agentchat.contrib.img_utils import extract_img_paths, get_image_data, gpt4v_formatter, llava_formater
except ImportError:
    skip = True
else:
    skip = False


base64_encoded_image = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4"
    "//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=="
)

raw_encoded_image = (
    "iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4"
    "//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg=="
)


@pytest.mark.skipif(skip, reason="dependency is not installed")
class TestGetImageData(unittest.TestCase):
    def test_http_image(self):
        with patch("requests.get") as mock_get:
            mock_response = requests.Response()
            mock_response.status_code = 200
            mock_response._content = b"fake image content"
            mock_get.return_value = mock_response

            result = get_image_data("http://example.com/image.png")
            self.assertEqual(result, base64.b64encode(b"fake image content").decode("utf-8"))

    def test_base64_encoded_image(self):
        result = get_image_data(base64_encoded_image)
        self.assertEqual(result, base64_encoded_image.split(",", 1)[1])

    def test_local_image(self):
        # Create a temporary file to simulate a local image file.
        temp_file = "_temp.png"

        image = Image.new("RGB", (60, 30), color=(73, 109, 137))
        image.save(temp_file)

        result = get_image_data(temp_file)
        with open(temp_file, "rb") as temp_image_file:
            temp_image_file.seek(0)
            expected_content = base64.b64encode(temp_image_file.read()).decode("utf-8")

        self.assertEqual(result, expected_content)
        os.remove(temp_file)


@pytest.mark.skipif(skip, reason="dependency is not installed")
class TestLlavaFormater(unittest.TestCase):
    def test_no_images(self):
        """
        Test the llava_formater function with a prompt containing no images.
        """
        prompt = "This is a test."
        expected_output = (prompt, [])
        result = llava_formater(prompt)
        self.assertEqual(result, expected_output)

    @patch("autogen.agentchat.contrib.img_utils.get_image_data")
    def test_with_images(self, mock_get_image_data):
        """
        Test the llava_formater function with a prompt containing images.
        """
        # Mock the get_image_data function to return a fixed string.
        mock_get_image_data.return_value = raw_encoded_image

        prompt = "This is a test with an image <img http://example.com/image.png>."
        expected_output = ("This is a test with an image <image>.", [raw_encoded_image])
        result = llava_formater(prompt)
        self.assertEqual(result, expected_output)

    @patch("autogen.agentchat.contrib.img_utils.get_image_data")
    def test_with_ordered_images(self, mock_get_image_data):
        """
        Test the llava_formater function with ordered image tokens.
        """
        # Mock the get_image_data function to return a fixed string.
        mock_get_image_data.return_value = raw_encoded_image

        prompt = "This is a test with an image <img http://example.com/image.png>."
        expected_output = ("This is a test with an image <image 0>.", [raw_encoded_image])
        result = llava_formater(prompt, order_image_tokens=True)
        self.assertEqual(result, expected_output)


@pytest.mark.skipif(skip, reason="dependency is not installed")
class TestGpt4vFormatter(unittest.TestCase):
    def test_no_images(self):
        """
        Test the gpt4v_formatter function with a prompt containing no images.
        """
        prompt = "This is a test."
        expected_output = [{"type": "text", "text": prompt}]
        result = gpt4v_formatter(prompt)
        self.assertEqual(result, expected_output)

    @patch("autogen.agentchat.contrib.img_utils.get_image_data")
    def test_with_images(self, mock_get_image_data):
        """
        Test the gpt4v_formatter function with a prompt containing images.
        """
        # Mock the get_image_data function to return a fixed string.
        mock_get_image_data.return_value = raw_encoded_image

        prompt = "This is a test with an image <img http://example.com/image.png>."
        expected_output = [
            {"type": "text", "text": "This is a test with an image "},
            {"type": "image_url", "image_url": {"url": base64_encoded_image}},
            {"type": "text", "text": "."},
        ]
        result = gpt4v_formatter(prompt)
        self.assertEqual(result, expected_output)

    @patch("autogen.agentchat.contrib.img_utils.get_image_data")
    def test_multiple_images(self, mock_get_image_data):
        """
        Test the gpt4v_formatter function with a prompt containing multiple images.
        """
        # Mock the get_image_data function to return a fixed string.
        mock_get_image_data.return_value = raw_encoded_image

        prompt = (
            "This is a test with images <img http://example.com/image1.png> and <img http://example.com/image2.png>."
        )
        expected_output = [
            {"type": "text", "text": "This is a test with images "},
            {"type": "image_url", "image_url": {"url": base64_encoded_image}},
            {"type": "text", "text": " and "},
            {"type": "image_url", "image_url": {"url": base64_encoded_image}},
            {"type": "text", "text": "."},
        ]
        result = gpt4v_formatter(prompt)
        self.assertEqual(result, expected_output)


@pytest.mark.skipif(skip, reason="dependency is not installed")
class TestExtractImgPaths(unittest.TestCase):
    def test_no_images(self):
        """
        Test the extract_img_paths function with a paragraph containing no images.
        """
        paragraph = "This is a test paragraph with no images."
        expected_output = []
        result = extract_img_paths(paragraph)
        self.assertEqual(result, expected_output)

    def test_with_images(self):
        """
        Test the extract_img_paths function with a paragraph containing images.
        """
        paragraph = (
            "This is a test paragraph with images http://example.com/image1.jpg and http://example.com/image2.png."
        )
        expected_output = ["http://example.com/image1.jpg", "http://example.com/image2.png"]
        result = extract_img_paths(paragraph)
        self.assertEqual(result, expected_output)

    def test_mixed_case(self):
        """
        Test the extract_img_paths function with mixed case image extensions.
        """
        paragraph = "Mixed case extensions http://example.com/image.JPG and http://example.com/image.Png."
        expected_output = ["http://example.com/image.JPG", "http://example.com/image.Png"]
        result = extract_img_paths(paragraph)
        self.assertEqual(result, expected_output)

    def test_local_paths(self):
        """
        Test the extract_img_paths function with local file paths.
        """
        paragraph = "Local paths image1.jpeg and image2.GIF."
        expected_output = ["image1.jpeg", "image2.GIF"]
        result = extract_img_paths(paragraph)
        self.assertEqual(result, expected_output)


if __name__ == "__main__":
    unittest.main()
