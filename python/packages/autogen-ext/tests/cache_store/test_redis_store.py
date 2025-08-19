import json
from typing import Any, List, Union, cast
from unittest.mock import MagicMock

import pytest
from autogen_core.models import CreateResult, RequestUsage
from pydantic import BaseModel

redis = pytest.importorskip("redis")


def test_redis_store_basic() -> None:
    from autogen_ext.cache_store.redis import RedisStore

    redis_instance = MagicMock()
    store = RedisStore[int](redis_instance)
    test_key = "test_key"
    test_value = 42
    store.set(test_key, test_value)
    redis_instance.set.assert_called_with(test_key, test_value)
    redis_instance.get.return_value = test_value
    assert store.get(test_key) == test_value

    new_value = 2
    store.set(test_key, new_value)
    redis_instance.set.assert_called_with(test_key, new_value)
    redis_instance.get.return_value = new_value
    assert store.get(test_key) == new_value

    key = "non_existent_key"
    default_value = 99
    redis_instance.get.return_value = None
    assert store.get(key, default_value) == default_value


def test_redis_with_different_instances() -> None:
    from autogen_ext.cache_store.redis import RedisStore

    redis_instance_1 = MagicMock()
    redis_instance_2 = MagicMock()

    store_1 = RedisStore[int](redis_instance_1)
    store_2 = RedisStore[int](redis_instance_2)

    test_key = "test_key"
    test_value_1 = 5
    test_value_2 = 6

    store_1.set(test_key, test_value_1)
    redis_instance_1.set.assert_called_with(test_key, test_value_1)
    redis_instance_1.get.return_value = test_value_1
    assert store_1.get(test_key) == test_value_1

    store_2.set(test_key, test_value_2)
    redis_instance_2.set.assert_called_with(test_key, test_value_2)
    redis_instance_2.get.return_value = test_value_2
    assert store_2.get(test_key) == test_value_2

    # test serialization
    store_1_config = store_1.dump_component()
    assert store_1_config.component_type == "cache_store"
    assert store_1_config.component_version == 1


class SampleModel(BaseModel):
    name: str
    value: int


class NestedModel(BaseModel):
    id: int
    data: str


class ComplexModel(BaseModel):
    sample: SampleModel
    nested: NestedModel
    tags: list[str]


def test_redis_store_serialization() -> None:
    from autogen_ext.cache_store.redis import RedisStore

    redis_instance = MagicMock()
    store = RedisStore[SampleModel](redis_instance)
    test_key = "test_model_key"
    test_model = SampleModel(name="test", value=42)

    # Test setting a Pydantic model
    store.set(test_key, test_model)

    # The Redis instance should be called with the serialized model
    args, _ = redis_instance.set.call_args
    assert args[0] == test_key
    assert isinstance(args[1], bytes)

    # Test retrieving a serialized model
    serialized_model = test_model.model_dump_json().encode("utf-8")
    redis_instance.get.return_value = serialized_model

    # When we retrieve, we get the JSON data back as a dict
    retrieved_model = store.get(test_key)
    assert retrieved_model is not None
    # The retrieved model should be a dict with the original data.
    assert isinstance(retrieved_model, dict)
    assert retrieved_model["name"] == "test"  # type: ignore
    assert retrieved_model["value"] == 42  # type: ignore

    # Test handling non-existent keys
    redis_instance.get.return_value = None
    assert store.get("non_existent_key") is None

    # Test fallback for non-model values
    redis_instance.get.return_value = b"simple string"
    simple_value = store.get("string_key")
    # Use cast to avoid type checking errors
    assert cast(str, simple_value) == "simple string"

    # Test error handling
    redis_instance.get.return_value = b"invalid json {["
    # Use cast to avoid type checking errors
    assert cast(str, store.get("invalid_json_key")) == "invalid json {["

    # Test exception during get - reset side_effect first
    redis_instance.get.side_effect = None
    redis_instance.get.side_effect = redis.RedisError("Redis error")
    assert store.get("error_key", default=SampleModel(name="default", value=0)) == SampleModel(name="default", value=0)

    # Test exception during set
    redis_instance.set.side_effect = redis.RedisError("Redis error")
    try:
        # This should not raise an exception due to our try/except block
        store.set("error_key", test_model)
    except Exception:
        pytest.fail("set() method didn't handle the exception properly")


def test_redis_store_nested_model_serialization() -> None:
    """Test serialization and deserialization of nested Pydantic models."""
    from autogen_ext.cache_store.redis import RedisStore

    redis_instance = MagicMock()
    store = RedisStore[ComplexModel](redis_instance)
    test_key = "test_complex_model_key"

    # Create a complex model with nested models
    test_complex_model = ComplexModel(
        sample=SampleModel(name="nested_test", value=100),
        nested=NestedModel(id=1, data="nested_data"),
        tags=["tag1", "tag2", "tag3"],
    )

    # Test setting a complex nested model
    store.set(test_key, test_complex_model)

    # Verify the Redis instance was called with serialized data
    args, _ = redis_instance.set.call_args
    assert args[0] == test_key
    assert isinstance(args[1], bytes)

    # Verify the serialized data can be deserialized back to the original structure
    serialized_json = args[1].decode("utf-8")
    deserialized_data = json.loads(serialized_json)

    assert deserialized_data["sample"]["name"] == "nested_test"
    assert deserialized_data["sample"]["value"] == 100
    assert deserialized_data["nested"]["id"] == 1
    assert deserialized_data["nested"]["data"] == "nested_data"
    assert deserialized_data["tags"] == ["tag1", "tag2", "tag3"]

    # Test retrieving the complex nested model
    serialized_model = test_complex_model.model_dump_json().encode("utf-8")
    redis_instance.get.return_value = serialized_model

    # When we retrieve, we get the JSON data back as a dict
    retrieved_model = store.get(test_key)
    assert retrieved_model is not None
    assert isinstance(retrieved_model, dict)
    assert retrieved_model["sample"]["name"] == "nested_test"  # type: ignore
    assert retrieved_model["sample"]["value"] == 100  # type: ignore
    assert retrieved_model["nested"]["id"] == 1  # type: ignore
    assert retrieved_model["nested"]["data"] == "nested_data"  # type: ignore
    assert retrieved_model["tags"] == ["tag1", "tag2", "tag3"]  # type: ignore


def test_redis_store_list_with_strings_only() -> None:
    """Test serialization of lists containing only strings (streaming scenario)."""
    from autogen_ext.cache_store.redis import RedisStore

    redis_instance = MagicMock()
    store = RedisStore[List[Union[str, CreateResult]]](redis_instance)
    test_key = "test_string_list_key"

    # Create a list with only strings (partial streaming result)
    string_list: List[Union[str, CreateResult]] = ["Hello", " world", "!", " How", " are", " you", "?"]

    # Test setting the list
    store.set(test_key, string_list)

    # Verify Redis was called with JSON-serialized data
    args, _ = redis_instance.set.call_args
    assert args[0] == test_key
    assert isinstance(args[1], bytes)

    # Verify the serialized data is correct
    serialized_json = args[1].decode("utf-8")
    deserialized_data = json.loads(serialized_json)
    assert deserialized_data == string_list

    # Test retrieving the list
    redis_instance.get.return_value = args[1]  # Return the serialized data
    retrieved_list = store.get(test_key)

    assert retrieved_list is not None
    assert isinstance(retrieved_list, list)
    assert retrieved_list == string_list


def test_redis_store_list_with_create_results_only() -> None:
    """Test serialization of lists containing only CreateResult objects."""
    from autogen_ext.cache_store.redis import RedisStore

    redis_instance = MagicMock()
    store = RedisStore[List[Union[str, CreateResult]]](redis_instance)
    test_key = "test_create_result_list_key"

    # Create a list with only CreateResult objects
    usage = RequestUsage(prompt_tokens=10, completion_tokens=20)
    create_result_list: List[Union[str, CreateResult]] = [
        CreateResult(content="First response", usage=usage, finish_reason="stop", cached=False),
        CreateResult(content="Second response", usage=usage, finish_reason="stop", cached=False),
    ]

    # Test setting the list
    store.set(test_key, create_result_list)

    # Verify Redis was called with JSON-serialized data
    args, _ = redis_instance.set.call_args
    assert args[0] == test_key
    assert isinstance(args[1], bytes)

    # Verify the serialized data structure
    serialized_json = args[1].decode("utf-8")
    deserialized_data = json.loads(serialized_json)

    assert isinstance(deserialized_data, list)
    # Type narrowing: after isinstance check, deserialized_data is known to be a list
    deserialized_list = deserialized_data  # Now properly typed as list
    assert len(deserialized_list) == 2
    assert deserialized_list[0]["content"] == "First response"
    assert deserialized_list[1]["content"] == "Second response"
    assert deserialized_list[0]["finish_reason"] == "stop"

    # Test retrieving the list
    redis_instance.get.return_value = args[1]  # Return the serialized data
    retrieved_list = store.get(test_key)

    assert retrieved_list is not None
    assert isinstance(retrieved_list, list)
    assert len(retrieved_list) == 2

    # The retrieved items should be dicts (as Redis returns JSON-parsed objects)
    assert isinstance(retrieved_list[0], dict)
    assert isinstance(retrieved_list[1], dict)
    assert retrieved_list[0]["content"] == "First response"  # type: ignore
    assert retrieved_list[1]["content"] == "Second response"  # type: ignore


def test_redis_store_mixed_list_streaming_scenario() -> None:
    """Test serialization of mixed lists (strings + CreateResult) for streaming cache scenario."""
    from autogen_ext.cache_store.redis import RedisStore

    redis_instance = MagicMock()
    store = RedisStore[List[Union[str, CreateResult]]](redis_instance)
    test_key = "test_mixed_streaming_list_key"

    # Create a mixed list simulating a streaming response
    usage = RequestUsage(prompt_tokens=15, completion_tokens=30)
    mixed_list: List[Union[str, CreateResult]] = [
        "The",
        " capital",
        " of",
        " France",
        " is",
        " Paris",
        ".",
        CreateResult(content="The capital of France is Paris.", usage=usage, finish_reason="stop", cached=False),
    ]

    # Test setting the mixed list
    store.set(test_key, mixed_list)

    # Verify Redis was called with JSON-serialized data
    args, _ = redis_instance.set.call_args
    assert args[0] == test_key
    assert isinstance(args[1], bytes)

    # Verify the serialized data structure
    serialized_json = args[1].decode("utf-8")
    deserialized_data = json.loads(serialized_json)

    assert isinstance(deserialized_data, list)
    # Type narrowing: after isinstance check, deserialized_data is known to be a list
    deserialized_list = deserialized_data  # Now properly typed as list
    assert len(deserialized_list) == 8  # 7 strings + 1 CreateResult

    # First 7 items should be strings
    for i in range(7):
        assert isinstance(deserialized_list[i], str)

    # Last item should be the serialized CreateResult (as dict)
    assert isinstance(deserialized_list[7], dict)
    assert deserialized_list[7]["content"] == "The capital of France is Paris."
    assert deserialized_list[7]["finish_reason"] == "stop"
    assert deserialized_data[7]["usage"]["prompt_tokens"] == 15
    assert deserialized_data[7]["usage"]["completion_tokens"] == 30

    # Test retrieving the mixed list
    redis_instance.get.return_value = args[1]  # Return the serialized data
    retrieved_list = store.get(test_key)

    assert retrieved_list is not None
    assert isinstance(retrieved_list, list)
    assert len(retrieved_list) == 8

    # First 7 items should still be strings
    for i in range(7):
        assert isinstance(retrieved_list[i], str)
        assert retrieved_list[i] == mixed_list[i]

    # Last item should be a dict (CreateResult deserialized from JSON)
    assert isinstance(retrieved_list[7], dict)
    assert retrieved_list[7]["content"] == "The capital of France is Paris."  # type: ignore
    assert retrieved_list[7]["cached"] is False  # type: ignore


def test_redis_store_empty_list() -> None:
    """Test serialization of empty lists."""
    from autogen_ext.cache_store.redis import RedisStore

    redis_instance = MagicMock()
    store = RedisStore[List[Union[str, CreateResult]]](redis_instance)
    test_key = "test_empty_list_key"

    # Test setting an empty list
    empty_list: List[Union[str, CreateResult]] = []
    store.set(test_key, empty_list)

    # Verify Redis was called with JSON-serialized data
    args, _ = redis_instance.set.call_args
    assert args[0] == test_key
    assert isinstance(args[1], bytes)

    # Verify the serialized data is an empty JSON array
    serialized_json = args[1].decode("utf-8")
    deserialized_data = json.loads(serialized_json)
    assert deserialized_data == []

    # Test retrieving the empty list
    redis_instance.get.return_value = args[1]
    retrieved_list = store.get(test_key)

    assert retrieved_list is not None
    assert isinstance(retrieved_list, list)
    assert len(retrieved_list) == 0


def test_redis_store_list_serialization_error_handling() -> None:
    """Test error handling during list serialization."""
    from autogen_ext.cache_store.redis import RedisStore

    redis_instance = MagicMock()
    store = RedisStore[List[Union[str, CreateResult]]](redis_instance)

    # Test Redis error during set
    redis_instance.set.side_effect = redis.RedisError("Redis connection failed")

    mixed_list: List[Union[str, CreateResult]] = [
        "test",
        CreateResult(
            content="test content",
            usage=RequestUsage(prompt_tokens=1, completion_tokens=1),
            finish_reason="stop",
            cached=False,
        ),
    ]

    # This should not raise an exception due to our try/except block
    try:
        store.set("error_key", mixed_list)
    except Exception:
        pytest.fail("set() method didn't handle the Redis exception properly")

    # Test get with corrupted JSON data for lists
    redis_instance.get.side_effect = None  # Reset side effect
    redis_instance.get.return_value = b'[{"invalid": json}]'  # Invalid JSON

    retrieved_value = store.get("corrupted_key", default=[])
    # Should return the decoded string when JSON parsing fails (backward compatibility)
    assert retrieved_value == '[{"invalid": json}]'  # type: ignore[comparison-overlap]
