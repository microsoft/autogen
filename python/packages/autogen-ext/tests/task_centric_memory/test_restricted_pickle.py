import io
import os
import pickle

import pytest

pytest.importorskip("chromadb")


def test_restricted_pickle_load_blocks_unsafe_globals(monkeypatch: pytest.MonkeyPatch) -> None:
    from autogen_ext.experimental.task_centric_memory.utils.restricted_pickle import (
        BASE_ALLOWED_PICKLE_GLOBALS,
        restricted_pickle_load,
    )

    monkeypatch.delenv("AUTOGEN_EXT_PICKLE_RCE_MARKER", raising=False)

    class Evil:
        def __reduce__(self):  # noqa: ANN001
            # Non-destructive: sets an env var if executed.
            return (
                exec,
                ("import os; os.environ['AUTOGEN_EXT_PICKLE_RCE_MARKER']='1'",),
            )

    payload = pickle.dumps(Evil())

    with pytest.raises(pickle.UnpicklingError):
        restricted_pickle_load(io.BytesIO(payload), allowed_globals=BASE_ALLOWED_PICKLE_GLOBALS)

    assert os.environ.get("AUTOGEN_EXT_PICKLE_RCE_MARKER") is None


def test_restricted_pickle_load_allows_memo_dict_roundtrip() -> None:
    from autogen_ext.experimental.task_centric_memory._memory_bank import Memo
    from autogen_ext.experimental.task_centric_memory.utils.restricted_pickle import (
        BASE_ALLOWED_PICKLE_GLOBALS,
        restricted_pickle_load,
    )

    allowed = BASE_ALLOWED_PICKLE_GLOBALS | {
        ("autogen_ext.experimental.task_centric_memory._memory_bank", "Memo"),
    }

    original = {"1": Memo(task=None, insight="hi")}
    payload = pickle.dumps(original)
    loaded = restricted_pickle_load(io.BytesIO(payload), allowed_globals=allowed)

    assert loaded == original
