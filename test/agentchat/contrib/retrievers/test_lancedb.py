import os
from pathlib import Path
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

# test_dir is 2 directories above this file
test_dir = Path(__file__).parent.parent.parent.parent / "test_files"


@pytest.mark.skipif(skip, reason="lancedb is not installed")
def test_lancedb(tmpdir):
    db = lancedb.connect(str(tmpdir))
    vectorstore = LanceDB(path=str(tmpdir))
    vectorstore.ingest_data(str(test_dir))

    assert "vectorstore" in db.table_names()

    results = vectorstore.query(["autogen"])
    assert isinstance(results, dict) and any("autogen" in res[0].lower() for res in results.get("documents", []))

    # Test index_exists()
    vectorstore = LanceDB(path=str(tmpdir))
    assert vectorstore.index_exists

    # Test use_existing_index()
    assert vectorstore.table is None
    vectorstore.use_existing_index()
    assert vectorstore.table is not None
