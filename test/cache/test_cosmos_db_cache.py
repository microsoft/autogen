#!/usr/bin/env python3 -m pytest

import pickle
import unittest
from unittest.mock import MagicMock, patch

import pytest

try:
    from autogen.cache.cosmos_db_cache import CosmosDBCache

    skip_cosmos_tests = False
except ImportError:
    skip_cosmos_tests = True

class TestCosmosDBCache(unittest.TestCase):
    def setUp(self):
        self.seed = "test_seed"
        self.client = MagicMock()
        self.database_id = "test_database"
        self.container_id = "test_container"

    @pytest.mark.skipif(skip_cosmos_tests, reason="Cosmos DB SDK not installed")
    @patch("autogen.cache.cosmos_db_cache.CosmosClient.from_connection_string", return_value=MagicMock())
    def test_init(self, mock_cosmos_from_connection_string):
        cache = CosmosDBCache(self.seed, self.client, self.database_id, self.container_id)
        self.assertEqual(cache.seed, self.seed)
        self.assertEqual(cache.client, self.client)

    @pytest.mark.skipif(skip_cosmos_tests, reason="Cosmos DB SDK not installed")
    def test_get(self):
        key = "key"
        value = "value"
        serialized_value = pickle.dumps(value)
        self.client.get_database_client().get_container_client().read_item.return_value = {"data": serialized_value}
        cache = CosmosDBCache(self.seed, self.client, self.database_id, self.container_id)

        self.assertEqual(cache.get(key), value)
        self.client.get_database_client().get_container_client().read_item.assert_called_with(
            item=key, partition_key=str(self.seed)
        )

        self.client.get_database_client().get_container_client().read_item.side_effect = Exception("not found")
        self.assertIsNone(cache.get(key))

    @pytest.mark.skipif(skip_cosmos_tests, reason="Cosmos DB SDK not installed")
    def test_set(self):
        key = "key"
        value = "value"
        serialized_value = pickle.dumps(value)
        cache = CosmosDBCache(self.seed, self.client, self.database_id, self.container_id)
        cache.set(key, value)
        self.client.get_database_client().get_container_client().upsert_item.assert_called_with(
            {"id": key, "partitionKey": str(self.seed), "data": serialized_value}
        )

    @pytest.mark.skipif(skip_cosmos_tests, reason="Cosmos DB SDK not installed")
    def test_context_manager(self):
        with CosmosDBCache(self.seed, self.client, self.database_id, self.container_id) as cache:
            self.assertIsInstance(cache, CosmosDBCache)
        # Note: Testing of close method if needed when CosmosClient requires explicit closing logic

if __name__ == "__main__":
    unittest.main()
