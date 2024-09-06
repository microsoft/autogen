import os
import sys

import pytest
from graphrag_sdk import KnowledgeGraph, Source
from graphrag_sdk.schema import Schema

sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))
from conftest import reason, skip_openai  # noqa: E402

try:
    from autogen.agentchat.contrib.graph_rag.document import (
        Document,
        DocumentType,
    )
    from autogen.agentchat.contrib.graph_rag.falkor_graph_query_engine import (
        FalkorGraphQueryEngine,
        GraphStoreQueryResult,
    )
except ImportError:
    skip = True
else:
    skip = False

reason = "do not run on MacOS or windows OR dependency is not installed OR " + reason


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or skip or skip_openai,
    reason=reason,
)
def test_falkor_db_query_engine():
    # Arrange
    test_schema = Schema()
    actor = test_schema.add_entity("Actor").add_attribute("name", str, unique=True)
    movie = test_schema.add_entity("Movie").add_attribute("title", str, unique=True)
    test_schema.add_relation("ACTED", actor, movie)

    query_engine = FalkorGraphQueryEngine(schema=test_schema)

    source_file = "test/agentchat/contrib/graph_rag/the_matrix.txt"
    input_docs = [Document(doctype=DocumentType.TEXT, path_or_url=source_file)]

    question = "Name a few actors who've played in 'The Matrix'"

    # Act
    query_engine.init_db(input_doc=input_docs)

    query_result: GraphStoreQueryResult = query_engine.query(question=question)

    # Assert
    assert query_result.answer.find("Keanu Reeves") >= 0
