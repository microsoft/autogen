from typing import cast
from unittest.mock import MagicMock, patch

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

    # Mock the BaseModel.model_validate_json to return our test model
    with patch("pydantic.BaseModel.model_validate_json", return_value=test_model):
        retrieved_model = store.get(test_key)
        assert retrieved_model is not None
        assert retrieved_model.name == "test"
        assert retrieved_model.value == 42

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

    # Test exception during get
    redis_instance.get.side_effect = Exception("Redis error")
    assert store.get("error_key", default=SampleModel(name="default", value=0)) == SampleModel(name="default", value=0)

    # Test exception during set
    redis_instance.set.side_effect = Exception("Redis error")
    try:
        # This should not raise an exception due to our try/except block
        store.set("error_key", test_model)
    except Exception:
        pytest.fail("set() method didn't handle the exception properly")
