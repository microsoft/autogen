"""Confirmation-gated TaskMarket Workbench for AutoGen."""

import asyncio
import hashlib
import inspect
import json
import math
import re
import shutil
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import ROUND_CEILING, Decimal, InvalidOperation
from typing import Any, Literal, cast

import httpx
from autogen_core import CancellationToken, Component
from autogen_core.tools import TextResultContent, ToolResult, ToolSchema, Workbench
from pydantic import BaseModel
from typing_extensions import Self

DEFAULT_API_URL = "https://api.taskmarket.dev"
DEFAULT_CLI = "taskmarket"
BASE_CHAIN_ID = 8453
USDC_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
PLATFORM_FEE_BPS = Decimal("750")
RELAY_FEE_USDC = Decimal("0.001")
USDC_QUANTUM = Decimal("0.000001")
PREVIEW_TTL = timedelta(minutes=15)
TaskMode = Literal["bounty", "claim", "pitch", "benchmark"]
SUPPORTED_MODES = frozenset({"bounty", "claim", "pitch", "benchmark"})
TaskMarketTransport = Callable[
    [str, str, dict[str, str], dict[str, Any] | None],
    dict[str, Any] | Awaitable[dict[str, Any]],
]
TaskMarketCliRunner = Callable[[list[str], bool], "_CliResult | Awaitable[_CliResult]"]


class TaskMarketWorkbenchConfig(BaseModel):
    """Serializable configuration for :class:`TaskMarketWorkbench`."""

    api_url: str = DEFAULT_API_URL
    cli_path: str = DEFAULT_CLI
    timeout: float = 15.0


@dataclass(frozen=True)
class _PendingPreview:
    request: dict[str, Any]
    deadline: datetime
    expires_at: datetime
    maximum_spend: Decimal


@dataclass(frozen=True)
class _CreationContext:
    pending: _PendingPreview
    request: dict[str, Any]
    confirmation_token: str


@dataclass(frozen=True)
class _CliResult:
    succeeded: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    ambiguous: bool = False


class TaskMarketWorkbench(Workbench, Component[TaskMarketWorkbenchConfig]):
    """Expose safe TaskMarket discovery and explicitly authorized requests.

    .. versionadded:: v0.7.6

    Read-only operations use TaskMarket's public HTTP API. Creating a task
    requires a matching preview, ``confirm=True``, an application-provided
    approval callback, and a Base/USDC balance preflight. The workbench never
    receives wallet private keys, accepts or rejects submissions, or retries
    an ambiguous CLI write.

    Args:
        api_url: TaskMarket API origin.
        cli_path: First-party ``taskmarket`` executable name or path.
        timeout: HTTP and CLI timeout in seconds.
        approval: Callback that reviews the exact preview and returns whether
            creation is authorized. It may be synchronous or asynchronous.

    Example:

        .. code-block:: python

            from autogen_ext.tools.taskmarket import TaskMarketWorkbench

            async with TaskMarketWorkbench() as workbench:
                tools = await workbench.list_tools()
                tasks = await workbench.call_tool("taskmarket_list_tasks", {"limit": 5})
    """

    component_provider_override = "autogen_ext.tools.taskmarket.TaskMarketWorkbench"
    component_config_schema = TaskMarketWorkbenchConfig

    def __init__(
        self,
        *,
        api_url: str = DEFAULT_API_URL,
        cli_path: str = DEFAULT_CLI,
        timeout: float = 15.0,
        approval: Callable[[dict[str, Any]], bool | Awaitable[bool]] | None = None,
        transport: TaskMarketTransport | None = None,
        cli_runner: TaskMarketCliRunner | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not api_url.strip():
            raise ValueError("`api_url` must not be empty")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("`timeout` must be a positive finite number")

        self.api_url = api_url.rstrip("/")
        self.cli_path = cli_path
        self.timeout = timeout
        self._approval = approval
        self._transport = transport
        self._cli_runner = cli_runner
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._pending_previews: dict[str, _PendingPreview] = {}
        self._schemas = _build_tool_schemas()

    async def list_tools(self) -> list[ToolSchema]:
        """List the TaskMarket tools exposed to an AutoGen agent."""
        return self._schemas

    async def call_tool(
        self,
        name: str,
        arguments: Mapping[str, Any] | None = None,
        cancellation_token: CancellationToken | None = None,
        call_id: str | None = None,
    ) -> ToolResult:
        """Call one TaskMarket tool and return a structured AutoGen result."""
        del call_id  # The public TaskMarket API does not use AutoGen call IDs.
        if name not in _TOOL_METHODS:
            return ToolResult(
                name=name,
                result=[TextResultContent(content=f"Tool `{name}` was not found.")],
                is_error=True,
            )

        invocation = asyncio.create_task(self._invoke(name, dict(arguments or {})))
        if cancellation_token is not None:
            cancellation_token.link_future(invocation)
        try:
            result = await invocation
        except Exception as exc:  # noqa: BLE001
            return ToolResult(
                name=name,
                result=[TextResultContent(content=f"TaskMarket tool failed: {exc}")],
                is_error=True,
            )
        return ToolResult(
            name=name,
            result=[TextResultContent(content=json.dumps(result, ensure_ascii=False, sort_keys=True))],
        )

    async def _invoke(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        method = cast(Callable[..., Awaitable[dict[str, Any]]], getattr(self, _TOOL_METHODS[name]))
        return await method(**arguments)

    async def list_tasks(
        self,
        status: str = "open",
        mode: str | None = None,
        tags: list[str] | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """List live public tasks without spending funds."""
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            return {"error": "`limit` must be between 1 and 100", "retry": False}
        params = {"status": status, "limit": str(limit)}
        if mode:
            params["mode"] = mode
        if tags:
            params["tags"] = ",".join(tag.strip() for tag in tags if tag.strip())
        return await self._request_json("GET", "/api/tasks", params=params)

    async def get_task(self, task_id: str) -> dict[str, Any]:
        """Retrieve current status for a task without changing it."""
        error = _validate_task_id(task_id)
        if error:
            return {"error": error, "retry": False}
        return await self._request_json("GET", f"/api/tasks/{task_id}")

    async def list_submissions(self, task_id: str) -> dict[str, Any]:
        """List submissions for application-level human review."""
        error = _validate_task_id(task_id)
        if error:
            return {"error": error, "retry": False}
        return await self._request_json("GET", f"/api/tasks/{task_id}/submissions")

    async def preview_task(
        self,
        description: str,
        reward_usdc: str,
        duration_hours: float,
        mode: TaskMode = "bounty",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Prepare a reviewable task request without spending funds."""
        try:
            request = _normalise_request(description, reward_usdc, duration_hours, mode, tags)
        except ValueError as exc:
            return {"error": str(exc), "retry": False}

        now = self._utc_now()
        try:
            deadline = now + timedelta(hours=float(request["durationHours"]))
        except (OverflowError, ValueError) as exc:
            return {"error": f"`duration_hours` is too large: {exc}", "retry": False}
        if deadline <= now:
            return {"error": "`duration_hours` must produce a future deadline", "retry": False}

        request["deadline"] = _format_datetime(deadline)
        maximum_spend = _maximum_spend(Decimal(request["rewardUsdc"]))
        request["maximumSpendUsdc"] = _format_usdc(maximum_spend)
        token = _confirmation_digest(request)
        expires_at = min(deadline, now + PREVIEW_TTL)
        self._pending_previews[token] = _PendingPreview(request, deadline, expires_at, maximum_spend)
        return {
            **request,
            "network": "Base",
            "chainId": BASE_CHAIN_ID,
            "currency": "USDC",
            "usdcContract": USDC_CONTRACT,
            "confirmationToken": token,
            "expiresAt": _format_datetime(expires_at),
        }

    async def create_task(
        self,
        description: str,
        reward_usdc: str,
        duration_hours: float,
        confirmation_token: str,
        confirm: bool = False,
        mode: TaskMode = "bounty",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create one task only after preview, approval, and wallet checks."""
        if not confirm:
            return {
                "error": (
                    "Creation is confirmation-gated. Review `taskmarket_preview_task` first, "
                    "then call `taskmarket_create_task` with `confirm=True`."
                ),
                "retry": False,
            }
        context = self._prepare_creation_context(
            description, reward_usdc, duration_hours, confirmation_token, mode, tags
        )
        if isinstance(context, dict):
            return context

        approval_error = await self._request_approval(context)
        if approval_error is not None:
            return approval_error

        preflight = await self._preflight_cli(context.pending.maximum_spend)
        if not preflight.succeeded:
            return {
                "error": preflight.error or "TaskMarket wallet preflight failed.",
                "retry": False,
                "status": "blocked",
            }

        cli_args = self._build_create_args(context)
        if isinstance(cli_args, dict):
            return cli_args
        result = await self._run_cli(cli_args, True)
        task_id = _task_id_from_cli_result(result.data)
        if not result.succeeded or task_id is None:
            if not result.succeeded:
                error = result.error or "Task creation failed; inspect live status before retrying."
                status = "unknown" if result.ambiguous else "failed"
            else:
                error = "The CLI returned no task ID. Inspect live status before retrying."
                status = "unknown"
            return {"error": error, "retry": False, "status": status}

        self._pending_previews.pop(context.confirmation_token, None)
        return {
            "taskId": task_id,
            "taskUrl": f"{self.api_url}/api/tasks/{task_id}",
            "status": "created",
            "retry": False,
        }

    def _prepare_creation_context(
        self,
        description: str,
        reward_usdc: str,
        duration_hours: float,
        confirmation_token: str,
        mode: TaskMode,
        tags: list[str] | None,
    ) -> dict[str, Any] | _CreationContext:
        if not confirmation_token:
            return {"error": "A `confirmation_token` from `taskmarket_preview_task` is required.", "retry": False}
        pending = self._pending_previews.get(confirmation_token)
        if pending is None:
            return {"error": "The preview is missing or has already been used.", "retry": False}
        now = self._utc_now()
        if now >= pending.expires_at or now >= pending.deadline:
            self._pending_previews.pop(confirmation_token, None)
            return {"error": "The preview expired. Run `taskmarket_preview_task` again.", "retry": False}
        try:
            request = _normalise_request(description, reward_usdc, duration_hours, mode, tags)
        except ValueError as exc:
            return {"error": str(exc), "retry": False}
        if request != {key: pending.request[key] for key in request}:
            return {
                "error": (
                    "The creation arguments differ from the reviewed preview. "
                    "Run `taskmarket_preview_task` again and review the new record."
                ),
                "retry": False,
            }
        return _CreationContext(pending, request, confirmation_token)

    async def _request_approval(self, context: _CreationContext) -> dict[str, Any] | None:
        if self._approval is None:
            return {
                "error": "No approval callback is configured; task creation is blocked.",
                "retry": False,
                "status": "blocked",
            }
        preview = {
            **context.pending.request,
            "network": "Base",
            "chainId": BASE_CHAIN_ID,
            "currency": "USDC",
            "usdcContract": USDC_CONTRACT,
            "confirmationToken": context.confirmation_token,
            "expiresAt": _format_datetime(context.pending.expires_at),
        }
        try:
            approved = self._approval(preview)
            if inspect.isawaitable(approved):
                approved = await approved
        except Exception as exc:  # noqa: BLE001
            return {"error": f"The approval callback failed: {exc}", "retry": False, "status": "blocked"}
        if not approved:
            return {
                "error": "The approval callback did not authorize task creation.",
                "retry": False,
                "status": "denied",
            }
        return None

    def _build_create_args(self, context: _CreationContext) -> list[str] | dict[str, Any]:
        remaining_hours = (context.pending.deadline - self._utc_now()).total_seconds() / 3600
        if remaining_hours <= 0:
            self._pending_previews.pop(context.confirmation_token, None)
            return {"error": "The reviewed deadline has passed. Run `taskmarket_preview_task` again.", "retry": False}
        args = [
            "task",
            "create",
            "--description",
            context.request["description"],
            "--reward",
            context.request["rewardUsdc"],
            "--duration",
            f"{remaining_hours:.9f}",
            "--mode",
            context.request["mode"],
        ]
        if context.request["tags"]:
            args.extend(["--tags", ",".join(context.request["tags"])])
        return args

    async def _preflight_cli(self, maximum_spend: Decimal) -> _CliResult:
        if self._cli_runner is None and shutil.which(self.cli_path) is None:
            return _CliResult(
                succeeded=False,
                error=(
                    "The first-party `taskmarket` CLI was not found. Install " "`@lucid-agents/taskmarket` and retry."
                ),
            )
        deposit = await self._run_cli(["deposit"], False)
        if not deposit.succeeded or deposit.data is None:
            return _CliResult(succeeded=False, error=deposit.error or "Could not verify TaskMarket wallet network.")
        expected = {
            "network": "Base",
            "chainId": BASE_CHAIN_ID,
            "currency": "USDC",
            "usdcContract": USDC_CONTRACT,
        }
        if any(deposit.data.get(key) != value for key, value in expected.items()):
            return _CliResult(succeeded=False, error="TaskMarket wallet is not configured for Base USDC.")

        stats = await self._run_cli(["stats"], False)
        if not stats.succeeded or stats.data is None:
            return _CliResult(succeeded=False, error=stats.error or "Could not verify available USDC balance.")
        try:
            balance = Decimal(str(stats.data["balanceUsdc"]))
        except (KeyError, InvalidOperation, TypeError, ValueError):
            return _CliResult(succeeded=False, error="TaskMarket CLI returned an unreadable USDC balance.")
        if not balance.is_finite() or balance < maximum_spend:
            return _CliResult(
                succeeded=False,
                error=f"Insufficient USDC balance for the reviewed maximum spend ({_format_usdc(maximum_spend)} USDC).",
            )
        return _CliResult(succeeded=True, data=stats.data)

    async def _run_cli(self, args: list[str], is_write: bool) -> _CliResult:
        if self._cli_runner is not None:
            result = self._cli_runner(args, is_write)
            if inspect.isawaitable(result):
                result = await result
            return result
        try:
            process = await asyncio.create_subprocess_exec(
                self.cli_path,
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, _stderr = await asyncio.wait_for(process.communicate(), timeout=self.timeout)
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                return _CliResult(
                    succeeded=False,
                    error=(
                        "TaskMarket CLI timed out. Inspect live status before retrying; " "the command was not retried."
                    ),
                    ambiguous=is_write,
                )
        except FileNotFoundError:
            return _CliResult(succeeded=False, error="The first-party `taskmarket` CLI was not found.")

        try:
            parsed: object = json.loads(stdout.decode())
        except (UnicodeDecodeError, json.JSONDecodeError):
            parsed = None
        if process.returncode == 0 and isinstance(parsed, dict):
            parsed_payload = cast(dict[str, Any], parsed)
            if parsed_payload.get("ok") is False:
                return _CliResult(succeeded=False, error="TaskMarket CLI rejected the command.", ambiguous=is_write)
            data = parsed_payload.get("data", parsed_payload)
            data_dict = cast(dict[str, Any], data) if isinstance(data, dict) else None
            return _CliResult(succeeded=data_dict is not None, data=data_dict)
        return _CliResult(succeeded=False, error="TaskMarket CLI rejected the command.", ambiguous=is_write)

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self._transport is not None:
            result = self._transport(method, path, params or {}, body)
            if inspect.isawaitable(result):
                result = await result
            return result
        try:
            async with httpx.AsyncClient(
                base_url=self.api_url,
                timeout=self.timeout,
                follow_redirects=False,
            ) as client:
                response = await client.request(method, path, params=params, json=body)
                response.raise_for_status()
                payload: object = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            return {"error": f"TaskMarket request failed: {exc}", "retry": True}
        if not isinstance(payload, dict):
            return {"error": "TaskMarket returned a non-object JSON response.", "retry": True}
        return cast(dict[str, Any], payload)

    async def start(self) -> None:
        """Start the workbench; no persistent connection is needed."""

    async def stop(self) -> None:
        """Stop the workbench; in-flight calls own their HTTP resources."""

    async def reset(self) -> None:
        """Clear uncommitted previews without changing wallet state."""
        self._pending_previews.clear()

    async def save_state(self) -> Mapping[str, Any]:
        """Return no state; approval-bound previews are intentionally ephemeral."""
        return {}

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Discard serialized state and clear any in-memory preview."""
        del state
        self._pending_previews.clear()

    def _to_config(self) -> TaskMarketWorkbenchConfig:
        return TaskMarketWorkbenchConfig(api_url=self.api_url, cli_path=self.cli_path, timeout=self.timeout)

    @classmethod
    def _from_config(cls, config: TaskMarketWorkbenchConfig) -> Self:
        return cls(api_url=config.api_url, cli_path=config.cli_path, timeout=config.timeout)

    def _utc_now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None:
            return now.replace(tzinfo=timezone.utc)
        return now.astimezone(timezone.utc)


_TOOL_METHODS = {
    "taskmarket_list_tasks": "list_tasks",
    "taskmarket_get_task": "get_task",
    "taskmarket_list_submissions": "list_submissions",
    "taskmarket_preview_task": "preview_task",
    "taskmarket_create_task": "create_task",
}


def _build_tool_schemas() -> list[ToolSchema]:
    return [
        _tool_schema(
            "taskmarket_list_tasks",
            "List live TaskMarket tasks without spending funds.",
            {
                "status": {"type": "string", "description": "Task status, such as open."},
                "mode": {"type": ["string", "null"], "description": "Optional task mode."},
                "tags": {"type": ["array", "null"], "items": {"type": "string"}},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100},
            },
        ),
        _tool_schema(
            "taskmarket_get_task",
            "Retrieve live status for one TaskMarket task.",
            {"task_id": {"type": "string", "description": "A 0x-prefixed 32-byte TaskMarket task ID."}},
            ["task_id"],
        ),
        _tool_schema(
            "taskmarket_list_submissions",
            "List TaskMarket submissions for human review only.",
            {"task_id": {"type": "string", "description": "A 0x-prefixed 32-byte TaskMarket task ID."}},
            ["task_id"],
        ),
        _tool_schema(
            "taskmarket_preview_task",
            "Prepare an exact TaskMarket request for review without spending funds.",
            {
                "description": {"type": "string"},
                "reward_usdc": {"type": "string", "description": "Positive USDC amount with at most 6 decimals."},
                "duration_hours": {"type": "number", "exclusiveMinimum": 0},
                "mode": {"type": "string", "enum": ["bounty", "claim", "pitch", "benchmark"]},
                "tags": {"type": ["array", "null"], "items": {"type": "string"}},
            },
            ["description", "reward_usdc", "duration_hours"],
        ),
        _tool_schema(
            "taskmarket_create_task",
            "Create a TaskMarket task only after a matching preview and application approval.",
            {
                "description": {"type": "string"},
                "reward_usdc": {"type": "string"},
                "duration_hours": {"type": "number", "exclusiveMinimum": 0},
                "confirmation_token": {"type": "string"},
                "confirm": {"type": "boolean"},
                "mode": {"type": "string", "enum": ["bounty", "claim", "pitch", "benchmark"]},
                "tags": {"type": ["array", "null"], "items": {"type": "string"}},
            },
            ["description", "reward_usdc", "duration_hours", "confirmation_token"],
        ),
    ]


def _tool_schema(
    name: str,
    description: str,
    properties: dict[str, Any],
    required: list[str] | None = None,
) -> ToolSchema:
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }
    return cast(ToolSchema, {"name": name, "description": description, "parameters": parameters})


def _validate_task_id(task_id: str) -> str | None:
    if not isinstance(task_id, str) or re.fullmatch(r"0x[0-9a-fA-F]{64}", task_id) is None:
        return "`task_id` must be a 0x-prefixed 32-byte TaskMarket task ID"
    return None


def _normalise_request(
    description: str,
    reward_usdc: str,
    duration_hours: float,
    mode: TaskMode,
    tags: list[str] | None,
) -> dict[str, Any]:
    if not isinstance(description, str) or not description.strip():
        raise ValueError("`description` must not be empty")
    try:
        reward = Decimal(str(reward_usdc).strip())
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("`reward_usdc` must be a positive USDC amount") from None
    if not reward.is_finite() or reward <= 0:
        raise ValueError("`reward_usdc` must be a positive USDC amount")
    exponent = reward.as_tuple().exponent
    if isinstance(exponent, str) or exponent < -6:
        raise ValueError("`reward_usdc` supports at most 6 decimal places")
    try:
        duration = Decimal(str(duration_hours))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("`duration_hours` must be a positive finite number") from None
    if not duration.is_finite() or duration <= 0:
        raise ValueError("`duration_hours` must be a positive finite number")
    if not isinstance(mode, str) or mode not in SUPPORTED_MODES:
        raise ValueError("`mode` must be one of: bounty, claim, pitch, benchmark")
    return {
        "description": description.strip(),
        "rewardUsdc": _format_usdc(reward),
        "durationHours": _format_decimal(duration),
        "mode": mode,
        "tags": [tag.strip() for tag in tags or [] if tag.strip()],
    }


def _format_usdc(value: Decimal) -> str:
    return f"{value.quantize(USDC_QUANTUM):.6f}"


def _format_decimal(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _format_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _maximum_spend(reward: Decimal) -> Decimal:
    fee = reward * PLATFORM_FEE_BPS / Decimal("10000")
    return (reward + fee + RELAY_FEE_USDC).quantize(USDC_QUANTUM, rounding=ROUND_CEILING)


def _confirmation_digest(request: dict[str, Any]) -> str:
    encoded = json.dumps(request, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _task_id_from_cli_result(data: dict[str, Any] | None) -> str | None:
    if data is None:
        return None
    task_id = data.get("taskId")
    return task_id if isinstance(task_id, str) and re.fullmatch(r"0x[0-9a-fA-F]{64}", task_id) else None


__all__ = ["TaskMarketWorkbench"]
