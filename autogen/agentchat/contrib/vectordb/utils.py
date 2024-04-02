import importlib
import logging
import time
from functools import wraps
from typing import Any

from termcolor import colored


class ColoredLogger(logging.Logger):
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)

    def debug(self, msg, *args, color=None, **kwargs):
        super().debug(colored(msg, color), *args, **kwargs)

    def info(self, msg, *args, color=None, **kwargs):
        super().info(colored(msg, color), *args, **kwargs)

    def warning(self, msg, *args, color="yellow", **kwargs):
        super().warning(colored(msg, color), *args, **kwargs)

    def error(self, msg, *args, color="light_red", **kwargs):
        super().error(colored(msg, color), *args, **kwargs)

    def critical(self, msg, *args, color="red", **kwargs):
        super().critical(colored(msg, color), *args, **kwargs)


def get_logger(name: str, level: int = logging.INFO) -> ColoredLogger:
    logger = ColoredLogger(name, level)
    console_handler = logging.StreamHandler()
    logger.addHandler(console_handler)
    formatter = logging.Formatter("%(asctime)s - %(filename)s:%(lineno)5d - %(levelname)s - %(message)s")
    logger.handlers[0].setFormatter(formatter)
    return logger


lazy_imported = {}
logger = get_logger(__name__)


def lazy_import(module_name: str, attr_name: str = None) -> Any:
    """lazy import module and attribute.

    Args:
        module_name: The name of the module to import.
        attr_name: The name of the attribute to import.

    Returns:
        The imported module or attribute.

    Example usage:
    ```python
    from autogen.agentchat.contrib.vectordb.utils import lazy_import
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
