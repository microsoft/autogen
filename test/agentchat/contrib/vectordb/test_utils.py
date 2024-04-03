#!/usr/bin/env python3 -m pytest

import pytest
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from conftest import skip_openai  # noqa: E402

from autogen.agentchat.contrib.vectordb.utils import filter_results_by_distance

skip = skip_openai


@pytest.mark.skipif(
    skip,
    reason="do not run for openai",
)
def test_retrieve_config():
    results = {
        "ids": [["id1", "id2"], ["id3", "id4"]],
        "contents": [
            ["content1", "content2"],
            [
                "content3",
                "content4",
            ],
        ],
        "embeddings": [
            [
                "embedding1",
                "embedding2",
            ],
            [
                "embedding3",
                "embedding4",
            ],
        ],
        "metadatas": [
            [
                "metadata1",
                "metadata2",
            ],
            [
                "metadata3",
                "metadata4",
            ],
        ],
        "distances": [[1, 2], [2, 3]],
    }
    print(filter_results_by_distance(results, 2.1))
    filter_results = {
        "ids": [["id1", "id2"], ["id3"]],
        "contents": [["content1", "content2"], ["content3"]],
        "embeddings": [["embedding1", "embedding2"], ["embedding3"]],
        "metadatas": [["metadata1", "metadata2"], ["metadata3"]],
        "distances": [[1, 2], [2]],
    }
    assert filter_results == filter_results_by_distance(results, 2.1)
