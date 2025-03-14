import tempfile

import pytest

diskcache = pytest.importorskip("diskcache")


def test_diskcache_store_basic() -> None:
    from autogen_ext.cache_store.diskcache import DiskCacheStore
    from diskcache import Cache

    with tempfile.TemporaryDirectory() as temp_dir, Cache(temp_dir) as cache:
        store = DiskCacheStore[int](cache)
        test_key = "test_key"
        test_value = 42
        store.set(test_key, test_value)
        assert store.get(test_key) == test_value

        new_value = 2
        store.set(test_key, new_value)
        assert store.get(test_key) == new_value

        key = "non_existent_key"
        default_value = 99
        assert store.get(key, default_value) == default_value


def test_diskcache_with_different_instances() -> None:
    from autogen_ext.cache_store.diskcache import DiskCacheStore
    from diskcache import Cache

    with (
        tempfile.TemporaryDirectory() as temp_dir_1,
        tempfile.TemporaryDirectory() as temp_dir_2,
        Cache(temp_dir_1) as cache_1,
        Cache(temp_dir_2) as cache_2,
    ):
        store_1 = DiskCacheStore[int](cache_1)
        store_2 = DiskCacheStore[int](cache_2)

        test_key = "test_key"
        test_value_1 = 5
        test_value_2 = 6

        store_1.set(test_key, test_value_1)
        assert store_1.get(test_key) == test_value_1

        store_2.set(test_key, test_value_2)
        assert store_2.get(test_key) == test_value_2

        # Test serialization
        store_1_config = store_1.dump_component()
        loaded_store_1: DiskCacheStore[int] = DiskCacheStore.load_component(store_1_config)
        assert loaded_store_1.get(test_key) == test_value_1
        loaded_store_1.cache.close()
