#!/usr/bin/env python3 -m pytest

import unittest
import pickle
from unittest.mock import patch, MagicMock

import pytest

try:
    from autogen.cache.redis_cache import RedisCache

    skip_redis_tests = False
except ImportError:
    skip_redis_tests = True


class TestRedisCache(unittest.TestCase):
    def setUp(self):
        self.seed = "test_seed"
        self.redis_url = "redis://localhost:6379/0"

    @pytest.mark.skipif(skip_redis_tests, reason="redis not installed")
    @patch("autogen.cache.redis_cache.redis.Redis.from_url", return_value=MagicMock())
    def test_init(self, mock_redis_from_url):
        cache = RedisCache(self.seed, self.redis_url)
        self.assertEqual(cache.seed, self.seed)
        mock_redis_from_url.assert_called_with(self.redis_url)

    @pytest.mark.skipif(skip_redis_tests, reason="redis not installed")
    @patch("autogen.cache.redis_cache.redis.Redis.from_url", return_value=MagicMock())
    def test_prefixed_key(self, mock_redis_from_url):
        cache = RedisCache(self.seed, self.redis_url)
        key = "test_key"
        expected_prefixed_key = f"autogen:{self.seed}:{key}"
        self.assertEqual(cache._prefixed_key(key), expected_prefixed_key)

    @pytest.mark.skipif(skip_redis_tests, reason="redis not installed")
    @patch("autogen.cache.redis_cache.redis.Redis.from_url", return_value=MagicMock())
    def test_get(self, mock_redis_from_url):
        key = "key"
        value = "value"
        serialized_value = pickle.dumps(value)
        cache = RedisCache(self.seed, self.redis_url)
        cache.cache.get.return_value = serialized_value
        self.assertEqual(cache.get(key), value)
        cache.cache.get.assert_called_with(f"autogen:{self.seed}:{key}")

        cache.cache.get.return_value = None
        self.assertIsNone(cache.get(key))

    @pytest.mark.skipif(skip_redis_tests, reason="redis not installed")
    @patch("autogen.cache.redis_cache.redis.Redis.from_url", return_value=MagicMock())
    def test_set(self, mock_redis_from_url):
        key = "key"
        value = "value"
        serialized_value = pickle.dumps(value)
        cache = RedisCache(self.seed, self.redis_url)
        cache.set(key, value)
        cache.cache.set.assert_called_with(f"autogen:{self.seed}:{key}", serialized_value)

    @pytest.mark.skipif(skip_redis_tests, reason="redis not installed")
    @patch("autogen.cache.redis_cache.redis.Redis.from_url", return_value=MagicMock())
    def test_context_manager(self, mock_redis_from_url):
        with RedisCache(self.seed, self.redis_url) as cache:
            self.assertIsInstance(cache, RedisCache)
            mock_redis_instance = cache.cache
        mock_redis_instance.close.assert_called()


if __name__ == "__main__":
    unittest.main()
