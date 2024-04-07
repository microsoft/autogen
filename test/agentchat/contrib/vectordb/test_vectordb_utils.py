#!/usr/bin/env python3 -m pytest

import os
import sys

import pytest

from autogen.agentchat.contrib.vectordb.utils import chroma_results_to_query_results, filter_results_by_distance


def test_retrieve_config():
    results = [
        [("id1", 1), ("id2", 2)],
        [("id3", 2), ("id4", 3)],
    ]
    print(filter_results_by_distance(results, 2.1))
    filter_results = [
        [("id1", 1), ("id2", 2)],
        [("id3", 2)],
    ]
    assert filter_results == filter_results_by_distance(results, 2.1)


def test_chroma_results_to_query_results():
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
    assert chroma_results_to_query_results(data_dict) == results
