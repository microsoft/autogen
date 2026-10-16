from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from autogenstudio.datamodel.eval import EvalTask

try:
    from openeval.types import OPENEVAL_VERSION
except ImportError:  # pragma: no cover - exercised when SDK is unavailable locally.
    OPENEVAL_VERSION = "unknown"


def _get_attr_or_item(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


def _task_payload(task: Any) -> dict[str, Any]:
    task_id = _get_attr_or_item(task, "task_id")
    input_data = _get_attr_or_item(task, "input")
    expected_outputs = _get_attr_or_item(task, "expected_outputs") or []
    metadata = _get_attr_or_item(task, "metadata") or {}
    name = _get_attr_or_item(task, "name", "")
    description = _get_attr_or_item(task, "description", "")

    return {
        "id": str(task_id),
        "input": input_data,
        "expected_output": expected_outputs[0] if expected_outputs else None,
        "expected_outputs": expected_outputs,
        "graders": ["gr_output_match"],
        "expected_tools": metadata.get("expected_tools", []),
        "name": name,
        "description": description,
    }


def to_openeval(eval_suite: Any) -> dict[str, Any]:
    """Convert an AutoGen eval suite into an OpenEval-compatible payload."""
    tasks = _get_attr_or_item(eval_suite, "tasks", [])
    if not isinstance(tasks, Sequence) or isinstance(tasks, (str, bytes)):
        tasks = [tasks]

    suite_id = _get_attr_or_item(eval_suite, "run_id", None) or _get_attr_or_item(eval_suite, "id", None) or "autogen_eval"
    return {
        "version": OPENEVAL_VERSION,
        "id": f"autogen_eval_{suite_id}",
        "test_cases": [_task_payload(task) for task in tasks if task is not None],
        "graders": [
            {
                "id": "gr_output_match",
                "type": "exact_match",
                "params": {"ignore_case": True},
            }
        ],
    }


def from_openeval(suite: Mapping[str, Any]) -> list[EvalTask]:
    """Convert an OpenEval suite into AutoGen eval tasks."""
    tasks = []
    for test_case in suite.get("test_cases", []):
        task = EvalTask(
            task_id=test_case["id"],
            input=test_case["input"],
            name=test_case.get("name", ""),
            description=test_case.get("description", ""),
            expected_outputs=[test_case.get("expected_output")] if test_case.get("expected_output") is not None else [],
            metadata={"expected_tools": test_case.get("expected_tools", [])},
        )
        tasks.append(task)
    return tasks
