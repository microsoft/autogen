from unittest.mock import MagicMock

import pytest

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
