#!/usr/bin/env python3 -m pytest

import pytest

import autogen
from autogen.oai.client_utils import validate_parameter


def test_validate_parameter():
    # Test valid parameters
    params = {
        "model": "Qwen/Qwen2-72B-Instruct",
        "max_tokens": 1000,
        "stream": False,
        "temperature": 1,
        "top_p": 0.8,
        "top_k": 50,
        "repetition_penalty": 0.5,
        "presence_penalty": 1.5,
        "frequency_penalty": 1.5,
        "min_p": 0.2,
        "safety_model": "Meta-Llama/Llama-Guard-7b",
    }

    # Should return the original value as they are valid
    assert params["model"] == validate_parameter(params, "model", str, False, None, None, None)
    assert params["max_tokens"] == validate_parameter(params, "max_tokens", int, True, 512, (0, None), None)
    assert params["stream"] == validate_parameter(params, "stream", bool, False, False, None, None)
    assert params["temperature"] == validate_parameter(params, "temperature", (int, float), True, None, None, None)
    assert params["top_k"] == validate_parameter(params, "top_k", int, True, None, None, None)
    assert params["repetition_penalty"] == validate_parameter(
        params, "repetition_penalty", float, True, None, None, None
    )
    assert params["presence_penalty"] == validate_parameter(
        params, "presence_penalty", (int, float), True, None, (-2, 2), None
    )
    assert params["safety_model"] == validate_parameter(params, "safety_model", str, True, None, None, None)

    # Test None allowed
    params = {
        "max_tokens": None,
    }

    # Should remain None
    assert validate_parameter(params, "max_tokens", int, True, 512, (0, None), None) is None

    # Test not None allowed
    params = {
        "max_tokens": None,
    }

    # Should return default
    assert 512 == validate_parameter(params, "max_tokens", int, False, 512, (0, None), None)

    # Test invalid parameters
    params = {
        "stream": "Yes",
        "temperature": "0.5",
        "top_p": "0.8",
        "top_k": "50",
        "repetition_penalty": "0.5",
        "presence_penalty": "1.5",
        "frequency_penalty": "1.5",
        "min_p": "0.2",
        "safety_model": False,
    }

    # Should all be set to defaults
    assert validate_parameter(params, "stream", bool, False, False, None, None) is not None
    assert validate_parameter(params, "temperature", (int, float), True, None, None, None) is None
    assert validate_parameter(params, "top_p", (int, float), True, None, None, None) is None
    assert validate_parameter(params, "top_k", int, True, None, None, None) is None
    assert validate_parameter(params, "repetition_penalty", float, True, None, None, None) is None
    assert validate_parameter(params, "presence_penalty", (int, float), True, None, (-2, 2), None) is None
    assert validate_parameter(params, "frequency_penalty", (int, float), True, None, (-2, 2), None) is None
    assert validate_parameter(params, "min_p", (int, float), True, None, (0, 1), None) is None
    assert validate_parameter(params, "safety_model", str, True, None, None, None) is None

    # Test parameters outside of bounds
    params = {
        "max_tokens": -200,
        "presence_penalty": -5,
        "frequency_penalty": 5,
        "min_p": -0.5,
    }

    # Should all be set to defaults
    assert 512 == validate_parameter(params, "max_tokens", int, True, 512, (0, None), None)
    assert validate_parameter(params, "presence_penalty", (int, float), True, None, (-2, 2), None) is None
    assert validate_parameter(params, "frequency_penalty", (int, float), True, None, (-2, 2), None) is None
    assert validate_parameter(params, "min_p", (int, float), True, None, (0, 1), None) is None

    # Test valid list options
    params = {
        "safety_model": "Meta-Llama/Llama-Guard-7b",
    }

    # Should all be set to defaults
    assert "Meta-Llama/Llama-Guard-7b" == validate_parameter(
        params, "safety_model", str, True, None, None, ["Meta-Llama/Llama-Guard-7b", "Meta-Llama/Llama-Guard-13b"]
    )

    # Test invalid list options
    params = {
        "stream": True,
    }

    # Should all be set to defaults
    assert not validate_parameter(params, "stream", bool, False, False, None, [False])

    # test invalid type
    params = {
        "temperature": None,
    }

    # should be set to defaults
    assert validate_parameter(params, "temperature", (int, float), False, 0.7, (0.0, 1.0), None) == 0.7

    # test value out of bounds
    params = {
        "temperature": 23,
    }

    # should be set to defaults
    assert validate_parameter(params, "temperature", (int, float), False, 1.0, (0.0, 1.0), None) == 1.0

    # type error for the parameters
    with pytest.raises(TypeError):
        validate_parameter({}, "param", str, True, None, None, "not_a_list")

    # passing empty params, which will set to defaults
    assert validate_parameter({}, "max_tokens", int, True, 512, (0, None), None) == 512


if __name__ == "__main__":
    test_validate_parameter()
