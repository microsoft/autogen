#!/usr/bin/env python3 -m pytest
import math
import os

import pytest

try:
    from autogen.oai.watsonx import WatsonxClient, calculate_watsonx_cost

    skip = False
except ImportError:
    WatsonxClient = object
    skip = True


reason = "Watsonx dependency not installed!"


@pytest.fixture()
def watsonx_client():
    return WatsonxClient(api_key="dummy_api_key", space_id="dummy_space_id")


@pytest.mark.skipif(skip, reason=reason)
def test_initialization_missing_api_key():
    os.environ.pop("WATSONX_API_KEY", None)
    with pytest.raises(
        AssertionError,
        match="Please include the api_key in your config list entry for Watsonx or set the WATSONX_API_KEY env variable.",
    ):
        WatsonxClient(space_id="dummy_space_id")

    WatsonxClient(api_key="dummy_api_key", space_id="dummy_space_id")


@pytest.mark.skipif(skip, reason=reason)
def test_intialization(watsonx_client):
    assert watsonx_client.api_key == "dummy_api_key", "`api_key` should be correctly set in the config"
    assert watsonx_client.space_id == "dummy_space_id", "`dummy_space_id` should be correctly set in the config"


@pytest.mark.skipif(skip, reason=reason)
def test_calculate_watsonx_cost():
    assert (
        calculate_watsonx_cost(0, 0, model_id="ibm/granite-3-8b-instruct") == 0.0
    ), "Cost should be 0 for 0 input_tokens and 0 output_tokens"
    assert math.isclose(calculate_watsonx_cost(1000, 2000, model_id="ibm/granite-3-8b-instruct"), 0.0006, rel_tol=0.01)


@pytest.mark.skipif(skip, reason=reason)
def test_load_config(watsonx_client):
    params = {
        "model": "ibm/granite-3-8b-instruct",
        "stream": False,
        "temperature": 1,
        "top_p": 0.8,
        "max_tokens": 100,
    }
    expected_params = {
        "temperature": 1,
        "top_p": 0.8,
        "max_tokens": 100,
        "frequency_penalty": None,
        "presence_penalty": None,
    }
    result = watsonx_client.parse_params(params)
    assert result == expected_params, "Config should be correctly loaded"
