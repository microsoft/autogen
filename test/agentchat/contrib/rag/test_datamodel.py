import unittest
from autogen.agentchat.contrib.rag.datamodel import Chunk, Document, QueryResults, Prompt


class TestChunk(unittest.TestCase):
    def test_chunk_creation(self):
        chunk = Chunk(title="Title", content="Content")
        self.assertEqual(chunk.title, "Title")
        self.assertEqual(chunk.content, "Content")
        self.assertIsNotNone(chunk.id)
        self.assertIsNone(chunk.metadata)

    def test_chunk_creation_with_id(self):
        chunk = Chunk(title="Title", content="Content", id="123")
        self.assertEqual(chunk.id, "123")

    def test_chunk_creation_with_metadata(self):
        metadata = {"source": "example", "date": "2022-01-01"}
        chunk = Chunk(title="Title", content="Content", metadata=metadata)
        self.assertEqual(chunk.metadata, metadata)

    def test_chunk_dict_conversion(self):
        chunk = Chunk(title="Title", content="Content")
        chunk_dict = chunk.dict()
        self.assertEqual(chunk_dict["title"], "Title")
        self.assertEqual(chunk_dict["content"], "Content")
        self.assertIsNotNone(chunk_dict["id"])
        self.assertIsNone(chunk_dict["metadata"])


class TestDocument(unittest.TestCase):
    def test_document_creation(self):
        document = Document(title="Title", content="Content")
        self.assertEqual(document.title, "Title")
        self.assertEqual(document.content, "Content")
        self.assertIsNotNone(document.id)
        self.assertIsNone(document.metadata)
        self.assertIsNone(document.title_embedding)
        self.assertIsNone(document.content_embedding)

    def test_document_creation_with_id(self):
        document = Document(title="Title", content="Content", id="123")
        self.assertEqual(document.id, "123")

    def test_document_creation_with_metadata(self):
        metadata = {"source": "example", "date": "2022-01-01"}
        document = Document(title="Title", content="Content", metadata=metadata)
        self.assertEqual(document.metadata, metadata)

    def test_document_dict_conversion(self):
        document = Document(title="Title", content="Content")
        document_dict = document.dict()
        self.assertEqual(document_dict["title"], "Title")
        self.assertEqual(document_dict["content"], "Content")
        self.assertIsNotNone(document_dict["id"])
        self.assertIsNone(document_dict["metadata"])
        self.assertIsNone(document_dict["title_embedding"])
        self.assertIsNone(document_dict["content_embedding"])


class TestQueryResults(unittest.TestCase):
    def test_query_results_creation(self):
        query_results = QueryResults(ids=[["1", "2"], ["3", "4"]])
        self.assertEqual(query_results.ids, [["1", "2"], ["3", "4"]])
        self.assertIsNone(query_results.texts)
        self.assertIsNone(query_results.embeddings)
        self.assertIsNone(query_results.metadatas)
        self.assertIsNone(query_results.distances)

    def test_query_results_dict_conversion(self):
        query_results = QueryResults(ids=[["1", "2"], ["3", "4"]])
        query_results_dict = query_results.dict()
        self.assertEqual(query_results_dict["ids"], [["1", "2"], ["3", "4"]])
        self.assertIsNone(query_results_dict["texts"])
        self.assertIsNone(query_results_dict["embeddings"])
        self.assertIsNone(query_results_dict["metadatas"])
        self.assertIsNone(query_results_dict["distances"])


class TestPrompt(unittest.TestCase):
    def test_prompt_creation(self):
        prompt = Prompt(type="qa", prompt="Question")
        self.assertEqual(prompt.type, "qa")
        self.assertEqual(prompt.prompt, "Question")
        self.assertIsNone(prompt.description)

    def test_prompt_creation_with_description(self):
        prompt = Prompt(type="qa", prompt="Question", description="Description")
        self.assertEqual(prompt.description, "Description")

    def test_prompt_dict_conversion(self):
        prompt = Prompt(type="qa", prompt="Question")
        prompt_dict = prompt.dict()
        self.assertEqual(prompt_dict["type"], "qa")
        self.assertEqual(prompt_dict["prompt"], "Question")
        self.assertIsNone(prompt_dict["description"])


if __name__ == "__main__":
    unittest.main()
