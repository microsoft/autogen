from pathlib import Path

import pandas as pd
import pytest
from agbench.tabulate_cmd import tabulate_cli


@pytest.mark.parametrize("option", ["--excel", "-e"])
@pytest.mark.parametrize("option_first", [False, True])
@pytest.mark.parametrize("csv", [False, True])
def test_excel_option_exports_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    option: str,
    option_first: bool,
    csv: bool,
) -> None:
    monkeypatch.chdir(tmp_path)
    runlogs = tmp_path / "results"
    instance = runlogs / "task-a" / "0"
    instance.mkdir(parents=True)
    (instance / "console_log.txt").write_text(
        "ALL TESTS PASSED !#!#\nSCENARIO.PY COMPLETE !#!#\nRUNTIME: 2.5 !#!#\n", encoding="utf-8"
    )
    output = tmp_path / "benchmark results.xlsx"
    args = [option, str(output), str(runlogs)] if option_first else [str(runlogs), option, str(output)]
    if csv:
        args.append("--csv")

    tabulate_cli(["agbench tabulate", *args])

    assert output.is_file()
    results = pd.read_excel(output)
    assert results.columns.tolist() == ["Task Id", "Trial 0 Success", "Trial 0 Time"]
    assert results.to_dict(orient="records") == [{"Task Id": "task-a", "Trial 0 Success": True, "Trial 0 Time": 2.5}]
    stdout = capsys.readouterr().out
    if csv:
        assert stdout.splitlines()[0] == "Task Id,Trial 0 Success,Trial 0 Time"
    else:
        assert "Summary Statistics" in stdout


@pytest.mark.parametrize("with_excel", [False, True])
def test_excel_output_argument_preserves_custom_tabulator_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], with_excel: bool
) -> None:
    monkeypatch.chdir(tmp_path)
    runlogs = tmp_path / "results"
    runlogs.mkdir()
    (runlogs / "custom_tabulate.py").write_text('def main(args):\n    print("custom tabulator")\n', encoding="utf-8")

    args = ["agbench tabulate", str(runlogs)]
    if with_excel:
        args.extend(["--excel", str(tmp_path / "results.xlsx")])
    tabulate_cli(args)

    assert capsys.readouterr().out == "custom tabulator\n"
