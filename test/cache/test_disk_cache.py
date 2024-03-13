#!/usr/bin/env python3 -m pytest

import unittest
from unittest.mock import patch, MagicMock
from autogen.cache.disk_cache import DiskCache


class TestDiskCache(unittest.TestCase):
    def setUp(self):
        self.seed = "test_seed"

    @patch("autogen.cache.disk_cache.diskcache.Cache", return_value=MagicMock())
    def test_init(self, mock_cache):
        cache = DiskCache(self.seed)
        self.assertIsInstance(cache.cache, MagicMock)
        mock_cache.assert_called_with(self.seed)

    @patch("autogen.cache.disk_cache.diskcache.Cache", return_value=MagicMock())
    def test_get(self, mock_cache):
        key = "key"
        value = "value"
        cache = DiskCache(self.seed)
        cache.cache.get.return_value = value
        self.assertEqual(cache.get(key), value)
        cache.cache.get.assert_called_with(key, None)

        cache.cache.get.return_value = None
        self.assertIsNone(cache.get(key, None))

    @patch("autogen.cache.disk_cache.diskcache.Cache", return_value=MagicMock())
    def test_set(self, mock_cache):
        key = "key"
        value = "value"
        cache = DiskCache(self.seed)
        cache.set(key, value)
        cache.cache.set.assert_called_with(key, value)

    @patch("autogen.cache.disk_cache.diskcache.Cache", return_value=MagicMock())
    def test_context_manager(self, mock_cache):
        with DiskCache(self.seed) as cache:
            self.assertIsInstance(cache, DiskCache)
            mock_cache_instance = cache.cache
        mock_cache_instance.close.assert_called()

    @patch("autogen.cache.disk_cache.diskcache.Cache", return_value=MagicMock())
    def test_close(self, mock_cache):
        cache = DiskCache(self.seed)
        cache.close()
        cache.cache.close.assert_called()


if __name__ == "__main__":
    unittest.main()
