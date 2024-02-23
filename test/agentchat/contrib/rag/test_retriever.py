import os
import sys
import unittest
from unittest.mock import MagicMock

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from conftest import skip_openai  # noqa: E402

try:
    import chromadb
    from openai import OpenAI

    from autogen.agentchat.contrib.rag.retriever import ChromaRetriever, Retriever, RetrieverFactory
except ImportError:
    skip = True
else:
    skip = False or skip_openai


@pytest.mark.skipif(skip, reason="dependency is not installed OR requested to skip")
class TestRetriever(unittest.TestCase):
    def test_retrieve_docs(self):
        retriever = Retriever("chroma", "collection", ".db")
        retriever.vector_db.retrieve_docs = MagicMock(return_value="query_results")
        queries = ["query1", "query2"]
        result = retriever.retrieve_docs(queries)
        retriever.vector_db.retrieve_docs.assert_called_once_with(queries=queries, collection_name="collection")
        self.assertEqual(result, "query_results")

    def test_get_docs_by_ids(self):
        retriever = Retriever("chroma", "collection", ".db")
        retriever.vector_db.get_docs_by_ids = MagicMock(return_value="get_results")
        ids = ["id1", "id2"]
        result = retriever.get_docs_by_ids(ids)
        retriever.vector_db.get_docs_by_ids.assert_called_once_with(ids=ids, collection_name="collection")
        self.assertEqual(result, "get_results")

    def test_convert_get_results_to_query_results(self):
        retriever = Retriever("chroma", "collection", ".db")
        retriever.vector_db.convert_get_results_to_query_results = MagicMock(return_value="query_results")
        get_result = "get_result"
        result = retriever.convert_get_results_to_query_results(get_result)
        retriever.vector_db.convert_get_results_to_query_results.assert_called_once_with(get_result)
        self.assertEqual(result, "query_results")


@pytest.mark.skipif(skip, reason="dependency is not installed OR requested to skip")
class TestChromaRetriever(unittest.TestCase):
    def test_init(self):
        retriever = ChromaRetriever("collection", ".db")
        self.assertEqual(retriever.db_type, "chroma")
        self.assertEqual(retriever.collection_name, "collection")
        self.assertEqual(retriever.path, ".db")
        self.assertEqual(retriever.encoder, None)
        self.assertEqual(retriever.db_config, None)
        self.assertEqual(retriever.name, "chroma")


@pytest.mark.skipif(skip, reason="dependency is not installed OR requested to skip")
class TestRetrieverFactory(unittest.TestCase):
    def test_create_retriever_chroma(self):
        retriever = RetrieverFactory.create_retriever("chroma", "collection")
        self.assertIsInstance(retriever, ChromaRetriever)
        self.assertEqual(retriever.collection_name, "collection")
        self.assertEqual(retriever.path, "./tmp/chroma")
        self.assertEqual(retriever.encoder, None)
        self.assertEqual(retriever.db_config, None)
        self.assertEqual(retriever.name, "chroma")

    def test_create_retriever_invalid(self):
        with self.assertRaises(ValueError):
            RetrieverFactory.create_retriever("invalid_retriever")


if __name__ == "__main__":
    unittest.main()
