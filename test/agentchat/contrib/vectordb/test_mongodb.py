import os
import sys
import time
import urllib.parse

import pytest
from conftest import reason

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

try:
    import sentence_transformers

    from autogen.agentchat.contrib.vectordb.mongodb import MongoDBAtlasVectorDB
except ImportError:
    skip = True
else:
    skip = False

reason = "do not run on MacOS or windows OR dependency is not installed OR " + reason


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or skip,
    reason=reason,
)
def test_mongodb():
    # test db config
    db_config = {
        "connection_string": "mongodb://mongodb_user:mongodb_password@localhost:27017/database_name",
    }

    # test create collection with connection_string authentication
    db = MongoDBAtlasVectorDB(
        connection_string=db_config["connection_string"],
    )
    collection_name = "test_collection"
    """
    def create_collection(collection_name: str,
                        overwrite: bool = False,
                        get_or_create: bool = True) -> Any
    Create a collection in the vector database.
    - Case 1. if the collection does not exist, create the collection.
    - Case 2. the collection exists, if overwrite is True, it will overwrite the collection.
    - Case 3. the collection exists and overwrite is False, if get_or_create is True, it will get the collection, otherwise it raise a ValueError.
    """
    # test_create_collection: case 1
    if collection_name not in db.list_collections():
        collection = db.create_collection(
            collection_name=collection_name,
            index_name="my_index",
            similarity="cosine",
            overwrite=False,
            get_or_create=True,
        )
        assert collection.name == collection_name

    # test_create_collection: case 2
    # test overwrite=True
    collection = db.create_collection(
        collection_name=collection_name,
        index_name="my_index_1",
        similarity="cosine",
        overwrite=True,
        get_or_create=True,
    )
    assert collection.name == collection_name

    # test_create_collection: case 3
    # test overwrite=False
    # test get_or_create=False
    with pytest.raises(ValueError):
        collection = db.create_collection(
            collection_name, index_name="my_index_1", similarity="cosine", overwrite=False, get_or_create=False
        )
    # test get_or_create=True
    collection = db.create_collection(
        collection_name, index_name="my_index_1", similarity="cosine", overwrite=False, get_or_create=True
    )
    assert collection.name == collection_name

    # test_get_collection
    collection = db.get_collection(collection_name)
    assert collection.name == collection_name

    # test_insert_docs
    docs = [{"content": "doc1", "id": "1"}, {"content": "doc2", "id": "2"}, {"content": "doc3", "id": "3"}]
    db.insert_docs(docs, collection_name, upsert=False)
    res = list(db.get_collection(collection_name).find({"id": {"$in": ["1", "2"]}}))
    final_results = [result.get("content") for result in res]
    assert final_results == ["doc1", "doc2"]

    # test_update_docs
    docs = [{"content": "doc11", "id": "1"}, {"content": "doc2", "id": "2"}, {"content": "doc3", "id": "3"}]
    db.update_docs(docs, collection_name)
    res = list(db.get_collection(collection_name).find({"id": {"$in": ["1", "2"]}}))
    final_results = [result.get("content") for result in res]
    assert final_results == ["doc11", "doc2"]

    # test_delete_docs
    ids = ["1"]
    db.delete_docs(ids, collection_name)
    res = list(db.get_collection(collection_name).find({"id": {"$in": ids}}))
    final_results = [result.get("content") for result in res]
    assert final_results == []

    # sleep for a few seconds -- make sure vector search index is ready
    time.sleep(30)
    # test_retrieve_docs
    """
    [[({'content': 'doc2', 'id': '2'}, 0.0),
    ({'content': 'doc3', 'id': '3'}, 0.08)],
    [({'content': 'doc3', 'id': '3'}, 0.0),
    ({'content': 'doc2', 'id': '2'}, 0.08)]]
    """
    queries = ["doc2", "doc3"]
    res = db.retrieve_docs(queries=queries, collection_name=collection_name, index_name="my_index_1")
    assert [[r[0]["id"] for r in rr] for rr in res] == [["2", "3"], ["3", "2"]]
    res = db.retrieve_docs(
        queries=queries, collection_name=collection_name, distance_threshold=0.05, index_name="my_index_1"
    )
    assert [[r[0]["id"] for r in rr] for rr in res] == [["2"], ["3"]]
    # test_get_docs_by_ids
    res = db.get_docs_by_ids(["1", "2"], collection_name)
    assert [r["id"] for r in res] == ["2"]  # "1" has been deleted
    res = db.get_docs_by_ids(collection_name=collection_name)
    assert set([r["id"] for r in res]) == set(["2", "3"])  # All Docs returned

    # test_delete_collection
    db.delete_collection(collection_name)
    # check if the collection is deleted
    pytest.raises(ValueError, db.get_collection, collection_name)


if __name__ == "__main__":
    test_mongodb()
