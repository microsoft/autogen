import os
import sys
import unittest

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

try:
    from autogen.agentchat.contrib.rag.utils import (
        flatten_list,
        lazy_import,
        merge_and_get_unique_in_turn_same_length,
        verify_one_arg,
    )
except ImportError:
    skip = True
else:
    skip = False


@pytest.mark.skipif(skip, reason="dependency is not installed OR requested to skip")
class TestUtils(unittest.TestCase):
    def test_lazy_import(self):
        # Test importing module
        os = lazy_import("os")
        self.assertIsNotNone(os)

        # Test importing attribute
        path = lazy_import("os", "path")
        self.assertIsNotNone(path)
        self.assertIs(os.path, path)

        # Test importing non-existent module
        non_existent_module = lazy_import("non_existent_module")
        self.assertIsNone(non_existent_module)

        # Test importing non-existent attribute
        non_existent_attr = lazy_import("os", "non_existent_attr")
        self.assertIsNone(non_existent_attr)

    def test_verify_one_arg(self):
        # Test with one argument specified
        self.assertIsNone(verify_one_arg(a=1, b=None, c=""))

        # Test with multiple arguments specified
        with self.assertRaises(ValueError):
            verify_one_arg(a=1, b=2, c=3)

        # Test with no arguments specified
        with self.assertRaises(ValueError):
            verify_one_arg()

    def test_flatten_list(self):
        # Test with nested list
        nested_list = [[1, 2, [3, 4]], [5, 6], 7, [8, [9, 10]]]
        flattened_list = flatten_list(nested_list)
        expected_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        self.assertEqual(flattened_list, expected_list)

        # Test with empty list
        empty_list = []
        flattened_empty_list = flatten_list(empty_list)
        self.assertEqual(flattened_empty_list, [])

    def test_merge_and_get_unique_in_turn_same_length(self):
        # Test with multiple lists
        list1 = [1, 2, 3, 4]
        list2 = [3, 4, 5, 6]
        list3 = [5, 6, 7, 8]
        merged_unique = merge_and_get_unique_in_turn_same_length(list1, list2, list3)
        expected_list = [1, 3, 5, 2, 4, 6, 7, 8]
        self.assertEqual(merged_unique, expected_list)

        # Test with empty lists
        empty_lists = []
        merged_empty_lists = merge_and_get_unique_in_turn_same_length(*empty_lists)
        self.assertEqual(merged_empty_lists, [])


if __name__ == "__main__":
    unittest.main()
