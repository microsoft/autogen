import os
import sys
import unittest

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

try:
    from autogen.agentchat.contrib.rag.promptgenerator import PromptGenerator, extract_refined_questions, verify_prompt
except ImportError:
    skip = True
else:
    skip = False


@pytest.mark.skipif(skip, reason="dependency is not installed OR requested to skip")
class TestPromptGenerator(unittest.TestCase):
    def setUp(self):
        self.prompt_generator = PromptGenerator()

    def test_extract_refined_questions(self):
        input_text = "1. What is the capital of France?... 2. Who wrote the book '1984'?"
        expected_output = ["What is the capital of France", "Who wrote the book '1984'"]
        self.assertEqual(extract_refined_questions(input_text), expected_output)

    def test_verify_prompt(self):
        prompt = "This is a {placeholder} prompt."
        contains = ["placeholder"]
        self.assertIsNone(verify_prompt(prompt, contains))

        prompt = "This is a {placeholder} prompt."
        contains = ["missing"]
        with self.assertRaises(ValueError):
            verify_prompt(prompt, contains)

    def test_call_llm(self):
        message = "Hello, how are you?"
        self.assertIsInstance(self.prompt_generator._call_llm(message), str)

    def test_prompt_generator(self):
        input_question = "What is the capital of France?"
        n = 3
        refined_message, prompt_rag = self.prompt_generator(input_question, n)
        self.assertIsInstance(refined_message, list)
        self.assertIsInstance(prompt_rag, str)

    def test_get_cost(self):
        cost = self.prompt_generator.get_cost()
        self.assertIsInstance(cost, dict)
        self.assertIn("nominal", cost)
        self.assertIn("actual", cost)


if __name__ == "__main__":
    unittest.main()
