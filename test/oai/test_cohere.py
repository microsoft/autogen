#!/usr/bin/env python3 -m pytest

import os

import pytest

try:
    from autogen.oai.cohere import CohereClient, calculate_cohere_cost

    skip = False
except ImportError:
    CohereClient = object
    skip = True


reason = "Cohere dependency not installed!"


@pytest.fixture()
def cohere_client():
    return CohereClient(api_key="dummy_api_key")


@pytest.mark.skipif(skip, reason=reason)
def test_initialization_missing_api_key():
    os.environ.pop("COHERE_API_KEY", None)
    with pytest.raises(
        AssertionError,
        match="Please include the api_key in your config list entry for Cohere or set the COHERE_API_KEY env variable.",
    ):
        CohereClient()

    CohereClient(api_key="dummy_api_key")


@pytest.mark.skipif(skip, reason=reason)
def test_intialization(cohere_client):
    assert cohere_client.api_key == "dummy_api_key", "`api_key` should be correctly set in the config"


@pytest.mark.skipif(skip, reason=reason)
def test_calculate_cohere_cost():
    assert (
        calculate_cohere_cost(0, 0, model="command-r") == 0.0
    ), "Cost should be 0 for 0 input_tokens and 0 output_tokens"
    assert calculate_cohere_cost(100, 200, model="command-r-plus") == 0.0033


@pytest.mark.skipif(skip, reason=reason)
def test_load_config(cohere_client):
    params = {
        "model": "command-r-plus",
        "stream": False,
        "temperature": 1,
        "p": 0.8,
        "max_tokens": 100,
    }
    expected_params = {
        "model": "command-r-plus",
        "temperature": 1,
        "p": 0.8,
        "seed": None,
        "max_tokens": 100,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "k": 0,
    }
    result = cohere_client.parse_params(params)
    assert result == expected_params, "Config should be correctly loaded"
