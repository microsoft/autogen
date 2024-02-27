import os
import sys
import unittest

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

try:
    from openai import OpenAI

    from autogen.agentchat.contrib.rag.reranker import Query, RerankerFactory, TfidfReranker
except ImportError:
    skip = True
else:
    skip = False


@pytest.mark.skipif(skip, reason="dependency is not installed OR requested to skip")
class TestTfidfReranker(unittest.TestCase):
    def setUp(self):
        self.reranker = TfidfReranker()
        self.docs = ["This is document 1", "This is document 2", "This is document 3"]
        self.query = Query("query", k=2)

    def test_vectorize(self):
        self.reranker.vectorize(self.docs)
        self.assertIsNotNone(self.reranker.corpus_tfidf)

    def test_rerank_return_docs(self):
        self.reranker.vectorize(self.docs)
        reranked_docs = self.reranker.rerank(self.query, docs=self.docs, return_docs=True)
        self.assertEqual(len(reranked_docs), self.query.k)
        self.assertIsInstance(reranked_docs[0], str)

    def test_rerank_return_scores(self):
        self.reranker.vectorize(self.docs)
        reranked_docs = self.reranker.rerank(self.query, docs=self.docs, return_scores=True)
        self.assertEqual(len(reranked_docs), self.query.k)
        self.assertIsInstance(reranked_docs[0], tuple)
        self.assertIsInstance(reranked_docs[0][0], int)
        self.assertIsInstance(reranked_docs[0][1], float)

    def test_rerank_return_docs_and_scores(self):
        self.reranker.vectorize(self.docs)
        reranked_docs = self.reranker.rerank(self.query, docs=self.docs, return_docs=True, return_scores=True)
        self.assertEqual(len(reranked_docs), self.query.k)
        self.assertIsInstance(reranked_docs[0], tuple)
        self.assertIsInstance(reranked_docs[0][0], str)
        self.assertIsInstance(reranked_docs[0][1], float)


@pytest.mark.skipif(skip, reason="dependency is not installed OR requested to skip")
class TestRerankerFactory(unittest.TestCase):
    def test_create_reranker_tfidf(self):
        reranker = RerankerFactory.create_reranker("tfidf")
        self.assertIsInstance(reranker, TfidfReranker)

    def test_create_reranker_invalid_name(self):
        with self.assertRaises(ValueError):
            RerankerFactory.create_reranker("invalid_reranker")


if __name__ == "__main__":
    unittest.main()
