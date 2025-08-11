import json
from typing import cast
from unittest.mock import MagicMock

import pytest
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
