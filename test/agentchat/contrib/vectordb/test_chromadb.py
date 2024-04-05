import os
import sys

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

try:
    import chromadb
    import sentence_transformers

    from autogen.agentchat.contrib.vectordb.chromadb import ChromaVectorDB
except ImportError:
    skip = True
else:
    skip = False


@pytest.mark.skipif(skip, reason="dependency is not installed OR requested to skip")
def test_chromadb():
    # test create collection
    db = ChromaVectorDB(path=".db")
    collection_name = "test_collection"
    collection = db.create_collection(collection_name, overwrite=True, get_or_create=True)
    assert collection.name == collection_name

    # test_delete_collection
    db.delete_collection(collection_name)
    pytest.raises(ValueError, db.get_collection, collection_name)

    # test more create collection
    collection = db.create_collection(collection_name, overwrite=False, get_or_create=False)
    assert collection.name == collection_name
    pytest.raises(ValueError, db.create_collection, collection_name, overwrite=False, get_or_create=False)
    collection = db.create_collection(collection_name, overwrite=True, get_or_create=False)
    assert collection.name == collection_name
    collection = db.create_collection(collection_name, overwrite=False, get_or_create=True)
    assert collection.name == collection_name

    # test_get_collection
    collection = db.get_collection(collection_name)
    assert collection.name == collection_name

    # test_insert_docs
    docs = [{"content": "doc1", "id": "1"}, {"content": "doc2", "id": "2"}, {"content": "doc3", "id": "3"}]
    db.insert_docs(docs, collection_name, upsert=False)
    res = db.get_collection(collection_name).get(["1", "2"])
    assert res["documents"] == ["doc1", "doc2"]

    # test_update_docs
    docs = [{"content": "doc11", "id": "1"}, {"content": "doc2", "id": "2"}, {"content": "doc3", "id": "3"}]
    db.update_docs(docs, collection_name)
    res = db.get_collection(collection_name).get(["1", "2"])
    assert res["documents"] == ["doc11", "doc2"]

    # test_delete_docs
    ids = ["1"]
    collection_name = "test_collection"
    db.delete_docs(ids, collection_name)
    res = db.get_collection(collection_name).get(ids)
    assert res["documents"] == []

    # test_retrieve_docs
    queries = ["doc2", "doc3"]
    collection_name = "test_collection"
    res = db.retrieve_docs(queries, collection_name)
    assert [[r[0]["id"] for r in rr] for rr in res] == [["2", "3"], ["3", "2"]]
    res = db.retrieve_docs(queries, collection_name, distance_threshold=0.1)
    print(res)
    assert [[r[0]["id"] for r in rr] for rr in res] == [["2"], ["3"]]

    # test _chroma_results_to_query_results
    data_dict = {
        "key1s": [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
        "key2s": [["a", "b", "c"], ["c", "d", "e"], ["e", "f", "g"]],
        "key3s": None,
        "key4s": [["x", "y", "z"], ["1", "2", "3"], ["4", "5", "6"]],
        "distances": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]],
    }
    results = [
        [
            ({"key1": 1, "key2": "a", "key4": "x"}, 0.1),
            ({"key1": 2, "key2": "b", "key4": "y"}, 0.2),
            ({"key1": 3, "key2": "c", "key4": "z"}, 0.3),
        ],
        [
            ({"key1": 4, "key2": "c", "key4": "1"}, 0.4),
            ({"key1": 5, "key2": "d", "key4": "2"}, 0.5),
            ({"key1": 6, "key2": "e", "key4": "3"}, 0.6),
        ],
        [
            ({"key1": 7, "key2": "e", "key4": "4"}, 0.7),
            ({"key1": 8, "key2": "f", "key4": "5"}, 0.8),
            ({"key1": 9, "key2": "g", "key4": "6"}, 0.9),
        ],
    ]
    assert db._chroma_results_to_query_results(data_dict) == results


if __name__ == "__main__":
    test_chromadb()
