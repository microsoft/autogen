import time
import logging
import importlib
from typing import Any, List
from functools import wraps
from termcolor import colored
from collections import deque


class MyLogger(logging.Logger):
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)

    def debug(self, msg, *args, color=None, **kwargs):
        super().debug(colored(msg, color), *args, **kwargs)

    def info(self, msg, *args, color=None, **kwargs):
        super().info(colored(msg, color), *args, **kwargs)

    def warning(self, msg, *args, color=None, **kwargs):
        super().warning(colored(msg, color), *args, **kwargs)

    def error(self, msg, *args, color=None, **kwargs):
        super().error(colored(msg, color), *args, **kwargs)

    def critical(self, msg, *args, color=None, **kwargs):
        super().critical(colored(msg, color), *args, **kwargs)


logger = MyLogger("autogen.agentchat.contrib.rag")
logger.setLevel(logging.INFO)
# Add a stream handler to print logs to console
console_handler = logging.StreamHandler()
logger.addHandler(console_handler)
# Set the format of the logs
formatter = logging.Formatter("%(asctime)s - %(filename)s:%(lineno)5d - %(levelname)s - %(message)s")
logger.handlers[0].setFormatter(formatter)

lazy_imported = {}


def lazy_import(module_name: str, attr_name: str = None) -> Any:
    """lazy import module and attribute.

    Args:
        module_name: The name of the module to import.
        attr_name: The name of the attribute to import.

    Returns:
        The imported module or attribute.

    Example usage:
    ```python
    from autogen.agentchat.contrib.rag.utils import lazy_import
    os = lazy_import("os")
    p = lazy_import("os", "path")
    print(os)
    print(p)
    print(os.path is p)  # True
    ```
    """
    if module_name not in lazy_imported:
        try:
            lazy_imported[module_name] = importlib.import_module(module_name)
        except ImportError:
            logger.error(f"Failed to import {module_name}.")
            return None
    if attr_name:
        attr = getattr(lazy_imported[module_name], attr_name, None)
        if attr is None:
            logger.error(f"Failed to import {attr_name} from {module_name}")
            return None
        else:
            return attr
    else:
        return lazy_imported[module_name]


def singleton(cls) -> Any:
    """
    Singleton decorator.
    """
    instances = {}

    def wrapper(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return wrapper


def verify_one_arg(**kwargs: Any) -> None:
    """
    Verify if only one of the arguments is not None or "".

    Example usage:
    ```python
    verify_one_arg(a=1, b=None, c="")  # pass
    ```
    """
    if sum([(arg is not None and arg != "") for arg in kwargs.values()]) != 1:
        _args = list(kwargs.keys())
        if len(_args) > 1:
            raise ValueError(f"Exactly one of {_args} must be specified.")
        else:
            raise ValueError(f"{_args[0]} must be specified.")


def timer(func) -> Any:
    """
    Timer decorator.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        logger.debug(f"{func.__name__} took {time.time() - start:.2f} seconds.")
        return result

    return wrapper


def flatten_list(lst) -> List[Any]:
    """
    Flatten a list of lists.

    Args:
        lst: List | A list of lists.

    Returns:
        List | The flattened list.

    Example usage:
    ```python
    nested_list = [[1, 2, [3, 4]], [5, 6], 7, [8, [9, 10]]]
    flattened_list = flatten_list(nested_list)
    print(flattened_list)  # [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    ```
    """
    flattened = []
    for item in lst:
        if isinstance(item, list):
            flattened.extend(flatten_list(item))
        else:
            flattened.append(item)
    return flattened


def merge_and_get_unique_in_turn_same_length(*lists: List[Any]) -> List[Any]:
    """
    To merge multiple lists, maintain the order of items, remove duplicates,
    and retrieve items from each list in turn.

    Args:
        lists: List | Multiple lists.

    Returns:
        List | The merged list with unique items.

    Example usage:
    ```python
    list1 = [1, 2, 3, 4]
    list2 = [3, 4, 5, 6]
    list3 = [5, 6, 7, 8]

    merged_unique = merge_and_get_unique_in_turn_same_length(list1, list2, list3)
    print(merged_unique)  # [1, 3, 5, 2, 4, 6, 7, 8]
    ```
    """
    seen = set()
    result = deque()
    list_length = len(lists[0])  # Assuming all lists have the same length

    for i in range(list_length):
        for lst in lists:
            item = lst[i]
            if item not in seen:
                result.append(item)
                seen.add(item)

    return list(result)
