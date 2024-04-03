from autogen.cache.in_memory_cache import InMemoryCache


def test_prefixed_key():
    cache = InMemoryCache(seed="test")
    assert cache._prefixed_key("key") == "test_key"


def test_get_with_default_value():
    cache = InMemoryCache()
    assert cache.get("key", "default_value") == "default_value"


def test_get_without_default_value():
    cache = InMemoryCache()
    assert cache.get("key") is None


def test_get_with_set_value():
    cache = InMemoryCache()
    cache.set("key", "value")
    assert cache.get("key") == "value"


def test_get_with_set_value_and_seed():
    cache = InMemoryCache(seed="test")
    cache.set("key", "value")
    assert cache.get("key") == "value"


def test_set():
    cache = InMemoryCache()
    cache.set("key", "value")
    assert cache._cache["key"] == "value"


def test_set_with_seed():
    cache = InMemoryCache(seed="test")
    cache.set("key", "value")
    assert cache._cache["test_key"] == "value"


def test_context_manager():
    with InMemoryCache() as cache:
        cache.set("key", "value")
        assert cache.get("key") == "value"
