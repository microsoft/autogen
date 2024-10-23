from autogen_ext.storage._base import Document
import pytest
from autogen_ext.storage import ChromaVectorDB
from chromadb.errors import ChromaError


# @pytest.mark.skipif(skip, reason="dependency is not installed")
def test_chromadb():
    # test create collection
    db = ChromaVectorDB(path=".db")
    collection_name = "test_collection"
    collection = db.create_collection(collection_name, overwrite=True, get_or_create=True)
    assert collection.name == collection_name

    # test_delete_collection
    db.delete_collection(collection_name)
    pytest.raises((ValueError, ChromaError), db.get_collection, collection_name)

    # test more create collection
    collection = db.create_collection(collection_name, overwrite=False, get_or_create=False)
    assert collection.name == collection_name
    pytest.raises(
        (ValueError, ChromaError), db.create_collection, collection_name, overwrite=False, get_or_create=False
    )
    collection = db.create_collection(collection_name, overwrite=True, get_or_create=False)
    assert collection.name == collection_name
    collection = db.create_collection(collection_name, overwrite=False, get_or_create=True)
    assert collection.name == collection_name

    # test_get_collection
    collection = db.get_collection(collection_name)
    assert collection.name == collection_name

    # test_insert_docs
    docs = [Document(content="doc1", id="1"), Document(content="doc2", id="2"), Document(content="doc3", id="3")]
    db.insert_docs(docs, collection_name, upsert=False)
    res = db.get_collection(collection_name).get(["1", "2"])
    assert res["documents"] == ["doc1", "doc2"]

    # test_update_docs
    docs = [Document(content="doc11", id="1"), Document(content="doc2", id="2"), Document(content="doc3", id="3")]
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
    assert [[r[0].id for r in rr] for rr in res] == [["2", "3"], ["3", "2"]]
    res = db.retrieve_docs(queries, collection_name, distance_threshold=0.1)
    assert [[r[0].id for r in rr] for rr in res] == [["2"], ["3"]]

    # test_get_docs_by_ids
    res = db.get_docs_by_ids(["1", "2"], collection_name)
    assert [r.id for r in res] == ["2"]  # "1" has been deleted
    res = db.get_docs_by_ids(collection_name=collection_name)
    assert [r.id for r in res] == ["2", "3"]

    # test _chroma_get_results_to_list_documents
    data_dict = {
        "key1s": [1, 2, 3],
        "key2s": ["a", "b", "c"],
        "key3s": None,
        "key4s": ["x", "y", "z"],
    }

    results = [
        {"key1": 1, "key2": "a", "key4": "x"},
        {"key1": 2, "key2": "b", "key4": "y"},
        {"key1": 3, "key2": "c", "key4": "z"},
    ]
    assert db._chroma_get_results_to_list_documents(data_dict) == results  # type: ignore
