from __future__ import annotations

import pickle
from typing import Any, BinaryIO

# NOTE: The task-centric memory feature persists local state to disk. These files
# can be moved between projects or restored from shared storage, so loads should
# not execute arbitrary pickle globals.

BASE_ALLOWED_PICKLE_GLOBALS: set[tuple[str, str]] = {
    ("builtins", "dict"),
    ("builtins", "list"),
    ("builtins", "set"),
    ("builtins", "tuple"),
    ("builtins", "str"),
    ("builtins", "bytes"),
    ("builtins", "bytearray"),
    ("builtins", "int"),
    ("builtins", "float"),
    ("builtins", "bool"),
}


class RestrictedUnpickler(pickle.Unpickler):
    def __init__(self, file: BinaryIO, allowed_globals: set[tuple[str, str]]) -> None:
        super().__init__(file)
        self._allowed_globals = allowed_globals

    def find_class(self, module: str, name: str):  # noqa: ANN001
        if (module, name) in self._allowed_globals:
            return super().find_class(module, name)
        raise pickle.UnpicklingError(
            f"Blocked global during unpickle: {module}.{name}. "
            "Delete the persisted memory files or re-run with reset=True."
        )


def restricted_pickle_load(file: BinaryIO, *, allowed_globals: set[tuple[str, str]]) -> Any:
    return RestrictedUnpickler(file, allowed_globals).load()

