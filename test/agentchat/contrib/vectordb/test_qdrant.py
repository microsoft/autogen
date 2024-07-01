import os
import sys

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

try:
    import uuid

    from qdrant_client import QdrantClient

    from autogen.agentchat.contrib.vectordb.qdrant import QdrantVectorDB
except ImportError:
    skip = True
else:
    skip = False


@pytest.mark.skipif(skip, reason="dependency is not installed")
def test_qdrant():
    # test create collection
    client = QdrantClient(location=":memory:")
    db = QdrantVectorDB(client=client)
    collection_name = uuid.uuid4().hex
    db.create_collection(collection_name, overwrite=True, get_or_create=True)
    assert client.collection_exists(collection_name)

    # test_delete_collection
    db.delete_collection(collection_name)
    assert not client.collection_exists(collection_name)

    # test_get_collection
    db.create_collection(collection_name, overwrite=True, get_or_create=True)
    collection_info = db.get_collection(collection_name)
    # Assert default FastEmbed model dimensions
    assert collection_info.config.params.vectors.size == 384

    # test_insert_docs
    docs = [{"content": "doc1", "id": 1}, {"content": "doc2", "id": 2}]
    db.insert_docs(docs, collection_name, upsert=False)
    res = db.get_docs_by_ids([1, 2], collection_name)
    assert res[0]["id"] == 1
    assert res[0]["content"] == "doc1"
    assert res[1]["id"] == 2
    assert res[1]["content"] == "doc2"

    # test_update_docs and get_docs_by_ids
    docs = [{"content": "doc11", "id": 1}, {"content": "doc22", "id": 2}]
    db.update_docs(docs, collection_name)
    res = db.get_docs_by_ids([1, 2], collection_name)
    assert res[0]["id"] == 1
    assert res[0]["content"] == "doc11"
    assert res[1]["id"] == 2
    assert res[1]["content"] == "doc22"

    # test_retrieve_docs
    queries = ["doc22", "doc11"]
    res = db.retrieve_docs(queries, collection_name)
    assert [[r[0]["id"] for r in rr] for rr in res] == [[2, 1], [1, 2]]

    # test_delete_docs
    db.delete_docs([1], collection_name)
    assert db.client.count(collection_name).count == 1


if __name__ == "__main__":
    test_qdrant()
