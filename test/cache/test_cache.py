#!/usr/bin/env python3 -m pytest

import unittest
from unittest.mock import patch, MagicMock
from autogen.cache.cache import Cache


class TestCache(unittest.TestCase):
    def setUp(self):
        self.config = {"cache_seed": "test_seed", "redis_url": "redis://test", "cache_path_root": ".test_cache"}

    @patch("autogen.cache.cache_factory.CacheFactory.cache_factory", return_value=MagicMock())
    def test_init(self, mock_cache_factory):
        cache = Cache(self.config)
        self.assertIsInstance(cache.cache, MagicMock)
        mock_cache_factory.assert_called_with("test_seed", "redis://test", ".test_cache")

    @patch("autogen.cache.cache_factory.CacheFactory.cache_factory", return_value=MagicMock())
    def test_context_manager(self, mock_cache_factory):
        mock_cache_instance = MagicMock()
        mock_cache_factory.return_value = mock_cache_instance

        with Cache(self.config) as cache:
            self.assertIsInstance(cache, MagicMock)

        mock_cache_instance.__enter__.assert_called()
        mock_cache_instance.__exit__.assert_called()

    @patch("autogen.cache.cache_factory.CacheFactory.cache_factory", return_value=MagicMock())
    def test_get_set(self, mock_cache_factory):
        key = "key"
        value = "value"
        mock_cache_instance = MagicMock()
        mock_cache_factory.return_value = mock_cache_instance

        cache = Cache(self.config)
        cache.set(key, value)
        cache.get(key)

        mock_cache_instance.set.assert_called_with(key, value)
        mock_cache_instance.get.assert_called_with(key, None)

    @patch("autogen.cache.cache_factory.CacheFactory.cache_factory", return_value=MagicMock())
    def test_close(self, mock_cache_factory):
        mock_cache_instance = MagicMock()
        mock_cache_factory.return_value = mock_cache_instance

        cache = Cache(self.config)
        cache.close()

        mock_cache_instance.close.assert_called()


if __name__ == "__main__":
    unittest.main()
