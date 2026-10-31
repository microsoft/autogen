import os

from agbench.tabulate_cmd import default_tabulate

SUCCESS_LOG = "ALL TESTS PASSED !#!#\nRUNTIME: 1.5 !#!#\n"


def _make_task(runlogs, task_id, trials, console_log=None):
    task_dir = os.path.join(str(runlogs), task_id)
    os.makedirs(task_dir)
    for trial in trials:
        trial_dir = os.path.join(task_dir, str(trial))
        os.makedirs(trial_dir)
        if console_log is not None:
            with open(os.path.join(trial_dir, "console_log.txt"), "wt") as fh:
                fh.write(console_log)
    return task_dir


def _rows(stdout):
    """Return the task rows of the plain-text table, keyed by task id."""
    rows = {}
    for line in stdout.splitlines():
        cells = line.split()
        for position, cell in enumerate(cells[:2]):
            if cell in {"alpha", "beta"}:
                rows[cell] = cells[position + 1 :]
    return rows


def test_task_without_trial_directories_does_not_abort_tabulation(tmp_path, capsys):
    _make_task(tmp_path, "alpha", [0, 1], SUCCESS_LOG)
    # A run that was interrupted before its first trial directory was created.
    _make_task(tmp_path, "beta", [])

    default_tabulate(["agbench", str(tmp_path)])

    captured = capsys.readouterr()
    rows = _rows(captured.out)
    assert set(rows) == {"alpha", "beta"}
    assert rows["alpha"] == ["True", "1.5", "True", "1.5"]
    assert "True" not in rows["beta"] and "1.5" not in rows["beta"]
    assert "Summary Statistics" in captured.out


def test_csv_output_without_trial_directories(tmp_path, capsys):
    _make_task(tmp_path, "alpha", [0], SUCCESS_LOG)
    _make_task(tmp_path, "beta", [])

    default_tabulate(["agbench", "--csv", str(tmp_path)])

    captured = capsys.readouterr()
    lines = [line for line in captured.out.splitlines() if line.strip()]
    assert lines[0] == "Task Id,Trial 0 Success,Trial 0 Time"
    assert any(line.startswith("beta,") for line in lines[1:])


def test_run_directory_without_any_trials(tmp_path, capsys):
    _make_task(tmp_path, "alpha", [])
    _make_task(tmp_path, "beta", [])

    default_tabulate(["agbench", str(tmp_path)])

    captured = capsys.readouterr()
    rows = _rows(captured.out)
    assert set(rows) == {"alpha", "beta"}


def test_trial_directories_not_numbered_are_ignored(tmp_path, capsys):
    task_dir = _make_task(tmp_path, "alpha", [0], SUCCESS_LOG)
    os.makedirs(os.path.join(task_dir, "logs"))

    default_tabulate(["agbench", str(tmp_path)])

    captured = capsys.readouterr()
    assert _rows(captured.out)["alpha"] == ["True", "1.5"]
