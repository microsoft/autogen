#!/usr/bin/env python3 -m pytest

import os
import sys

import pytest

from autogen.agentchat.contrib.vectordb.utils import filter_results_by_distance


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
