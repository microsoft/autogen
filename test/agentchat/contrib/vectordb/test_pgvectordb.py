import os
import sys
import urllib.parse

import pytest
from conftest import reason

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

try:
    import pgvector
    import psycopg
    import sentence_transformers

    from autogen.agentchat.contrib.vectordb.pgvectordb import PGVectorDB
except ImportError:
    skip = True
else:
    skip = False

reason = "do not run on MacOS or windows OR dependency is not installed OR " + reason


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or skip,
    reason=reason,
)
def test_pgvector():
    # test db config
    db_config = {
        "connection_string": "postgresql://postgres:postgres@localhost:5432/postgres",
    }

    # test create collection with connection_string authentication
    db = PGVectorDB(
        connection_string=db_config["connection_string"],
    )
    collection_name = "test_collection"
    collection = db.create_collection(collection_name=collection_name, overwrite=True, get_or_create=True)
    assert collection.name == collection_name

    # test create collection with conn object authentication
    parsed_connection = urllib.parse.urlparse(db_config["connection_string"])
    encoded_username = urllib.parse.quote(parsed_connection.username, safe="")
    encoded_password = urllib.parse.quote(parsed_connection.password, safe="")
    encoded_host = urllib.parse.quote(parsed_connection.hostname, safe="")
    encoded_database = urllib.parse.quote(parsed_connection.path[1:], safe="")
    connection_string_encoded = (
        f"{parsed_connection.scheme}://{encoded_username}:{encoded_password}"
        f"@{encoded_host}:{parsed_connection.port}/{encoded_database}"
    )
    conn = psycopg.connect(conninfo=connection_string_encoded, autocommit=True)

    db = PGVectorDB(conn=conn)
    collection_name = "test_collection"
    collection = db.create_collection(collection_name=collection_name, overwrite=True, get_or_create=True)
    assert collection.name == collection_name

    # test create collection with basic authentication
    db_config = {
        "username": "postgres",
        "password": os.environ.get("POSTGRES_PASSWORD", default="postgres"),
        "host": "localhost",
        "port": 5432,
        "dbname": "postgres",
    }

    db = PGVectorDB(
        username=db_config["username"],
        password=db_config["password"],
        port=db_config["port"],
        host=db_config["host"],
        dbname=db_config["dbname"],
    )
    collection_name = "test_collection"
    collection = db.create_collection(collection_name=collection_name, overwrite=True, get_or_create=True)
    assert collection.name == collection_name

    # test_delete_collection
    db.delete_collection(collection_name)
    assert collection.table_exists(table_name=collection_name) is False

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
    res = db.get_collection(collection_name).get(ids=["1", "2"])
    final_results = [result.get("content") for result in res]
    assert final_results == ["doc1", "doc2"]

    # test_update_docs
    docs = [{"content": "doc11", "id": "1"}, {"content": "doc2", "id": "2"}, {"content": "doc3", "id": "3"}]
    db.update_docs(docs, collection_name)
    res = db.get_collection(collection_name).get(["1", "2"])
    final_results = [result.get("content") for result in res]
    assert final_results == ["doc11", "doc2"]

    # test_delete_docs
    ids = ["1"]
    collection_name = "test_collection"
    db.delete_docs(ids, collection_name)
    res = db.get_collection(collection_name).get(ids)
    final_results = [result.get("content") for result in res]
    assert final_results == []

    # test_retrieve_docs
    queries = ["doc2", "doc3"]
    collection_name = "test_collection"
    res = db.retrieve_docs(queries, collection_name)
    assert [[r[0]["id"] for r in rr] for rr in res] == [["2", "3"], ["3", "2"]]
    res = db.retrieve_docs(queries, collection_name, distance_threshold=0.1)
    assert [[r[0]["id"] for r in rr] for rr in res] == [["2"], ["3"]]

    # test_get_docs_by_ids
    res = db.get_docs_by_ids(["1", "2"], collection_name)
    assert [r["id"] for r in res] == ["2"]  # "1" has been deleted
    res = db.get_docs_by_ids(collection_name=collection_name)
    assert set([r["id"] for r in res]) == set(["2", "3"])  # All Docs returned


if __name__ == "__main__":
    test_pgvector()
