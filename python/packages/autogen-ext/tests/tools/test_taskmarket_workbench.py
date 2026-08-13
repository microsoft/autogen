import json
from datetime import datetime, timezone
from typing import Any

import pytest
from autogen_ext.tools.taskmarket import TaskMarketWorkbench
from autogen_ext.tools.taskmarket._workbench import USDC_CONTRACT, _CliResult  # pyright: ignore[reportPrivateUsage]

TASK_ID = "0x" + "a" * 64


@pytest.mark.asyncio
async def test_taskmarket_workbench_lists_live_tasks() -> None:
    calls: list[tuple[str, str, dict[str, str], Any]] = []

    async def transport(
        method: str,
        path: str,
        params: dict[str, str],
        body: Any,
    ) -> dict[str, Any]:
        calls.append((method, path, params, body))
        return {"tasks": [{"id": "0xabc", "status": "open"}]}

    workbench = TaskMarketWorkbench(transport=transport)
    result = await workbench.call_tool("taskmarket_list_tasks", {"status": "open", "limit": 1})

    assert result.is_error is False
    assert result.to_text() == '{"tasks": [{"id": "0xabc", "status": "open"}]}'
    assert calls == [("GET", "/api/tasks", {"status": "open", "limit": "1"}, None)]


@pytest.mark.asyncio
async def test_taskmarket_workbench_reads_task_and_submissions() -> None:
    calls: list[tuple[str, str, dict[str, str], Any]] = []

    async def transport(
        method: str,
        path: str,
        params: dict[str, str],
        body: Any,
    ) -> dict[str, Any]:
        calls.append((method, path, params, body))
        return {"path": path}

    workbench = TaskMarketWorkbench(transport=transport)
    task = await workbench.call_tool("taskmarket_get_task", {"task_id": TASK_ID})
    submissions = await workbench.call_tool("taskmarket_list_submissions", {"task_id": TASK_ID})

    assert json.loads(task.to_text()) == {"path": f"/api/tasks/{TASK_ID}"}
    assert json.loads(submissions.to_text()) == {"path": f"/api/tasks/{TASK_ID}/submissions"}
    assert calls == [
        ("GET", f"/api/tasks/{TASK_ID}", {}, None),
        ("GET", f"/api/tasks/{TASK_ID}/submissions", {}, None),
    ]


@pytest.mark.asyncio
async def test_taskmarket_preview_contains_exact_base_usdc_budget() -> None:
    now = datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc)
    workbench = TaskMarketWorkbench(clock=lambda: now)

    result = await workbench.call_tool(
        "taskmarket_preview_task",
        {
            "description": "Deliver a tested AutoGen workbench",
            "reward_usdc": "1.00",
            "duration_hours": 4,
            "mode": "bounty",
            "tags": ["python", "agents"],
        },
    )
    preview = json.loads(result.to_text())

    assert preview["rewardUsdc"] == "1.000000"
    assert preview["deadline"] == "2026-08-13T16:00:00Z"
    assert preview["maximumSpendUsdc"] == "1.076000"
    assert preview["network"] == "Base"
    assert preview["chainId"] == 8453
    assert preview["currency"] == "USDC"
    assert preview["usdcContract"] == USDC_CONTRACT
    assert len(preview["confirmationToken"]) == 64


@pytest.mark.asyncio
async def test_taskmarket_create_requires_confirmation_before_cli() -> None:
    calls: list[tuple[list[str], bool]] = []

    async def cli_runner(args: list[str], is_write: bool) -> _CliResult:
        calls.append((args, is_write))
        return _CliResult(succeeded=True, data={"taskId": TASK_ID})

    workbench = TaskMarketWorkbench(cli_runner=cli_runner, approval=lambda _preview: True)
    result = await workbench.call_tool(
        "taskmarket_create_task",
        {
            "description": "Deliver a tested AutoGen workbench",
            "reward_usdc": "1",
            "duration_hours": 4,
            "confirmation_token": "not-previewed",
            "confirm": False,
        },
    )

    assert result.is_error is False
    assert "confirmation-gated" in result.to_text()
    assert calls == []


@pytest.mark.asyncio
async def test_taskmarket_create_runs_one_approved_cli_flow() -> None:
    now = datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc)
    calls: list[tuple[list[str], bool]] = []
    approvals: list[dict[str, Any]] = []

    async def cli_runner(args: list[str], is_write: bool) -> _CliResult:
        calls.append((args, is_write))
        if args == ["deposit"]:
            return _CliResult(
                succeeded=True,
                data={"network": "Base", "chainId": 8453, "currency": "USDC", "usdcContract": USDC_CONTRACT},
            )
        if args == ["stats"]:
            return _CliResult(succeeded=True, data={"balanceUsdc": "5"})
        return _CliResult(succeeded=True, data={"taskId": TASK_ID})

    def approve(preview: dict[str, Any]) -> bool:
        approvals.append(preview)
        return True

    workbench = TaskMarketWorkbench(clock=lambda: now, cli_runner=cli_runner, approval=approve)
    preview_result = await workbench.call_tool(
        "taskmarket_preview_task",
        {"description": "Deliver a tested AutoGen workbench", "reward_usdc": "1", "duration_hours": 4},
    )
    preview = json.loads(preview_result.to_text())
    result = await workbench.call_tool(
        "taskmarket_create_task",
        {
            "description": "Deliver a tested AutoGen workbench",
            "reward_usdc": "1",
            "duration_hours": 4,
            "confirmation_token": preview["confirmationToken"],
            "confirm": True,
        },
    )

    assert json.loads(result.to_text()) == {
        "retry": False,
        "status": "created",
        "taskId": TASK_ID,
        "taskUrl": f"https://api.taskmarket.dev/api/tasks/{TASK_ID}",
    }
    assert len(approvals) == 1
    assert calls[0] == (["deposit"], False)
    assert calls[1] == (["stats"], False)
    assert calls[2][0][:2] == ["task", "create"]
    assert calls[2][1] is True


@pytest.mark.asyncio
async def test_taskmarket_create_does_not_retry_ambiguous_cli_write() -> None:
    calls: list[tuple[list[str], bool]] = []

    async def cli_runner(args: list[str], is_write: bool) -> _CliResult:
        calls.append((args, is_write))
        if args == ["deposit"]:
            return _CliResult(
                succeeded=True,
                data={"network": "Base", "chainId": 8453, "currency": "USDC", "usdcContract": USDC_CONTRACT},
            )
        if args == ["stats"]:
            return _CliResult(succeeded=True, data={"balanceUsdc": "5"})
        return _CliResult(succeeded=False, error="timed out", ambiguous=True)

    workbench = TaskMarketWorkbench(cli_runner=cli_runner, approval=lambda _preview: True)
    preview_result = await workbench.call_tool(
        "taskmarket_preview_task",
        {"description": "Deliver a tested AutoGen workbench", "reward_usdc": "1", "duration_hours": 4},
    )
    preview = json.loads(preview_result.to_text())
    result = await workbench.call_tool(
        "taskmarket_create_task",
        {
            "description": "Deliver a tested AutoGen workbench",
            "reward_usdc": "1",
            "duration_hours": 4,
            "confirmation_token": preview["confirmationToken"],
            "confirm": True,
        },
    )

    body = json.loads(result.to_text())
    assert body["status"] == "unknown"
    assert body["retry"] is False
    assert len(calls) == 3
    assert calls[-1][1] is True


@pytest.mark.asyncio
async def test_taskmarket_workbench_does_not_serialize_pending_previews() -> None:
    workbench = TaskMarketWorkbench()
    state = await workbench.save_state()

    assert state == {}
    await workbench.load_state({"unexpected": "state"})
