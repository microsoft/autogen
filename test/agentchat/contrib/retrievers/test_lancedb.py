import numpy as np
from pathlib import Path
import pytest

try:
    from autogen.agentchat.contrib.retriever.lancedb import LanceDB
    import lancedb
except ImportError:
    skip = True
else:
    skip = False


test_dir = Path(__file__).parent.parent.parent.parent / "test_files"


def embedding_fcn(texts):
    return [np.array([0, 0]) for _ in texts]


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

    vectorstore.ingest_data(str(test_dir), overwrite=True)
    vectorstore.query(["hello"])

    vectorstore = LanceDB(path=str(tmpdir), embedding_function=embedding_fcn)
    vectorstore.ingest_data(str(test_dir), overwrite=True)
