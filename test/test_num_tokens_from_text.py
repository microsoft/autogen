import unittest
from autogen.retrieve_utils import num_tokens_from_text

class TestNumTokensFromText(unittest.TestCase):

    def test_known_model(self):
        # Test with a known model and known token counts
        text = "This is a test message."
        model = "gpt-3.5-turbo-0613"
        result = num_tokens_from_text(text, model)
        self.assertEqual(result, 6)  # Adjust the expected token count

    def test_unknown_model(self):
        # Test with an unknown model
        text = "This is a test message."
        model = "unknown-model"
        with self.assertRaises(NotImplementedError):
            num_tokens_from_text(text, model)

if __name__ == '__main__':
    unittest.main()
