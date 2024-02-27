import os
import sys

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

try:
    from autogen.agentchat.contrib.rag.datamodel import Chunk, Document, GetResults, Query, QueryResults
except ImportError:
    skip = True
else:
    skip = False


@pytest.mark.skipif(skip, reason="dependency not installed OR requested to skip")
def test_chunk():
    chunk = Chunk(content="This is a test chunk")
    assert chunk.content == "This is a test chunk"
    assert chunk.id is not None
    assert chunk.metadata is None


@pytest.mark.skipif(skip, reason="dependency not installed OR requested to skip")
def test_document():
    document = Document(
        content="This is a test document", content_embedding=[1, 2, 3], embedding_model="model", dimensions=3
    )
    assert document.content == "This is a test document"
    assert document.content_embedding == [1, 2, 3]
    assert document.embedding_model == "model"
    assert document.dimensions == 3


@pytest.mark.skipif(skip, reason="dependency not installed OR requested to skip")
def test_query_results():
    query_results = QueryResults(ids=[["1", "2", "3"], ["4", "5", "6"]])
    assert query_results.ids == [["1", "2", "3"], ["4", "5", "6"]]
    assert query_results.texts is None
    assert query_results.embeddings is None
    assert query_results.metadatas is None
    assert query_results.distances is None


@pytest.mark.skipif(skip, reason="dependency not installed OR requested to skip")
def test_query():
    query = Query(text="This is a test query", k=5, filter_metadata={"source": "example"}, include=["texts"])
    assert query.text == "This is a test query"
    assert query.k == 5
    assert query.filter_metadata == {"source": "example"}
    assert query.filter_document is None
    assert query.include == ["texts"]


@pytest.mark.skipif(skip, reason="dependency not installed OR requested to skip")
def test_get_results():
    get_results = GetResults(ids=["1", "2", "3"], texts=["Document 1", "Document 2", "Document 3"])
    assert get_results.ids == ["1", "2", "3"]
    assert get_results.texts == ["Document 1", "Document 2", "Document 3"]
    assert get_results.embeddings is None
    assert get_results.metadatas is None


if __name__ == "__main__":
    pytest.main()
