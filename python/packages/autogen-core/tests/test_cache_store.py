from unittest.mock import Mock

from autogen_core import CacheStore


def test_set_and_get_object_key_value() -> None:
    mock_store = Mock(spec=CacheStore)
    test_key = object()
    test_value = object()
    mock_store.set(test_key, test_value)
    mock_store.get.return_value = test_value
    mock_store.set.assert_called_with(test_key, test_value)
    assert mock_store.get(test_key) == test_value


def test_get_non_existent_key() -> None:
    mock_store = Mock(spec=CacheStore)
    key = "non_existent_key"
    mock_store.get.return_value = None
    assert mock_store.get(key) is None


def test_set_overwrite_existing_key() -> None:
    mock_store = Mock(spec=CacheStore)
    key = "test_key"
    initial_value = "initial_value"
    new_value = "new_value"
    mock_store.set(key, initial_value)
    mock_store.set(key, new_value)
    mock_store.get.return_value = new_value
    mock_store.set.assert_called_with(key, new_value)
    assert mock_store.get(key) == new_value
