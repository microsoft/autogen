import os
import re
from pathlib import Path

import pytest
from agbench.tabulate_cmd import default_tabulate


@pytest.mark.parametrize("trial_counts", [(3, 1), (1, 3), (3, 3)])
def test_summary_includes_trials_from_every_task(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], trial_counts: tuple[int, int]
) -> None:
    for task_index, trial_count in enumerate(trial_counts):
        task_dir = tmp_path / f"task_{task_index}"
        task_dir.mkdir()
        for trial in range(trial_count):
            instance_dir = task_dir / str(trial)
            instance_dir.mkdir()
            (instance_dir / "console_log.txt").write_text(
                ("ALL TESTS PASSED !#!#\n" if trial != 2 else "") + "SCENARIO.PY COMPLETE !#!#\nRUNTIME: 2.0 !#!#\n",
                encoding="utf-8",
            )
        # The command orders tasks by mtime, not by name.
        os.utime(task_dir, (1_700_000_000 + task_index, 1_700_000_000 + task_index))

    default_tabulate(["agbench tabulate", str(tmp_path)])

    summary = capsys.readouterr().out.split("Summary Statistics", 1)[1]
    completed_counts = [2, sum(count > 1 for count in trial_counts), sum(count > 2 for count in trial_counts)]
    for trial, completed in enumerate(completed_counts):
        successes = completed if trial != 2 else 0
        failures = completed if trial == 2 else 0
        # Check successes, failures, missing results and total task count.
        assert re.search(rf"^Trial {trial}\s+{successes}\s+{failures}\s+{2 - completed}\s+2\s", summary, re.MULTILINE)
    expected_all_successes = "0.5" if 1 in trial_counts else "0"
    assert re.search(rf"^Trial Aggregated\s+1\s+{re.escape(expected_all_successes)}\s*$", summary, re.MULTILINE)
