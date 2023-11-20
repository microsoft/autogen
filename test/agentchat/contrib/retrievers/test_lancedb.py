import os
import pytest
from autogen.agentchat.contrib.retriever.retrieve_utils import (
    split_text_to_chunks,
    extract_text_from_pdf,
    split_files_to_chunks,
    get_files_from_dir,
    is_url,
)
try:
    from autogen.agentchat.contrib.retriever.lancedb import LanceDB
    import lancedb
except ImportError:
    skip = True
else:
    skip = False
    
test_dir = os.path.join(os.path.dirname(__file__), "test_files")

@pytest.mark.skipif(skip, reason="lancedb is not installed")
def test_lancedb():
    db_path = "/tmp/test_lancedb_store"
    db = lancedb.connect(db_path)
    if os.path.exists(db_path):
        vectorstore = LanceDB(path=db_path, use_existing=True)
    else:
        vectorstore = LanceDB(path=db_path)
    vectorstore.ingest_data(test_dir)
    
    assert "vectorstore" in db.table_names()
    
    results = vectorstore.query(["autogen"])
    assert isinstance(results, dict) and any("autogen" in res[0].lower() for res in results.get("documents", []))
