# Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
#
# SPDX-License-Identifier: Apache-2.0
#
# Portions derived from  https://github.com/microsoft/autogen are under the MIT License.
# SPDX-License-Identifier: MIT
import unittest

from url_shortener import retrieve_url, shorten_url


class TestURLShortener(unittest.TestCase):
    def test_url_retrieval(self):
        # Shorten the URL to get its shortened form
        shortened_url = shorten_url("https://www.example.com")

        # Retrieve the original URL using the shortened URL directly
        retrieved_url = retrieve_url(shortened_url)

        self.assertEqual(
            retrieved_url,
            "https://www.example.com",
            "Retrieved URL does not match the original!",
        )


if __name__ == "__main__":
    unittest.main()
