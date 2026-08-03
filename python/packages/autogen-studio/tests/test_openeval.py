from autogenstudio.datamodel.eval import EvalTask
from autogenstudio.eval import from_openeval, to_openeval


def test_to_openeval_round_trip():
    tasks = [
        EvalTask(
            task_id="task-1",
            input="question-1",
            name="Task 1",
            description="desc-1",
            expected_outputs=["answer-1"],
            metadata={"expected_tools": ["tool-a"]},
        ),
        EvalTask(
            task_id="task-2",
            input=["prompt", "image"],
            expected_outputs=[],
            metadata={},
        ),
    ]

    suite = to_openeval({"run_id": "run-42", "tasks": tasks})

    assert suite["version"]
    assert suite["id"] == "autogen_eval_run-42"
    assert suite["graders"][0]["id"] == "gr_output_match"
    assert suite["test_cases"][0]["id"] == "task-1"
    assert suite["test_cases"][0]["expected_output"] == "answer-1"
    assert suite["test_cases"][0]["expected_tools"] == ["tool-a"]
    assert suite["test_cases"][1]["expected_output"] is None

    imported = from_openeval(suite)
    assert imported[0].task_id == "task-1"
    assert imported[0].input == "question-1"
    assert imported[0].expected_outputs == ["answer-1"]
    assert imported[1].task_id == "task-2"
    assert imported[1].metadata == {"expected_tools": []}
