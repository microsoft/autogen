import unittest
from unittest.mock import MagicMock
from autogen.agentchat.contrib.rag.retriever import Retriever, ChromaRetriever, RetrieverFactory


class TestRetriever(unittest.TestCase):
    def test_retrieve_docs(self):
        retriever = Retriever("chroma", "collection", "path")
        retriever.vector_db.retrieve_docs = MagicMock(return_value="query_results")
        queries = ["query1", "query2"]
        result = retriever.retrieve_docs(queries)
        retriever.vector_db.retrieve_docs.assert_called_once_with(queries=queries, collection_name="collection")
        self.assertEqual(result, "query_results")

    def test_get_docs_by_ids(self):
        retriever = Retriever("chroma", "collection", "path")
        retriever.vector_db.get_docs_by_ids = MagicMock(return_value="get_results")
        ids = ["id1", "id2"]
        result = retriever.get_docs_by_ids(ids)
        retriever.vector_db.get_docs_by_ids.assert_called_once_with(ids=ids, collection_name="collection")
        self.assertEqual(result, "get_results")

    def test_convert_get_results_to_query_results(self):
        retriever = Retriever("chroma", "collection", "path")
        retriever.vector_db.convert_get_results_to_query_results = MagicMock(return_value="query_results")
        get_result = "get_result"
        result = retriever.convert_get_results_to_query_results(get_result)
        retriever.vector_db.convert_get_results_to_query_results.assert_called_once_with(get_result)
        self.assertEqual(result, "query_results")


class TestChromaRetriever(unittest.TestCase):
    def test_init(self):
        retriever = ChromaRetriever("collection", "path")
        self.assertEqual(retriever.db_type, "chroma")
        self.assertEqual(retriever.collection_name, "collection")
        self.assertEqual(retriever.path, "path")
        self.assertEqual(retriever.encoder, None)
        self.assertEqual(retriever.db_config, None)
        self.assertEqual(retriever.name, "chroma")


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
