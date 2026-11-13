# AutoGen Extensions

- [Documentation](https://microsoft.github.io/autogen/stable/user-guide/extensions-user-guide/index.html)

AutoGen is designed to be extensible. The `autogen-ext` package contains many different component implementations maintained by the AutoGen project. However, we strongly encourage others to build their own components and publish them as part of the ecosytem.

## TaskMarket Workbench

`TaskMarketWorkbench` provides an AutoGen `Workbench` for discovering public
TaskMarket tasks and, when an application explicitly authorizes it, creating a
task through the first-party `taskmarket` CLI.

Install the optional HTTP dependency with:

```bash
pip install "autogen-ext[taskmarket]"
```

Read-only discovery does not require wallet credentials:

```python
from autogen_ext.tools.taskmarket import TaskMarketWorkbench

async with TaskMarketWorkbench() as workbench:
    result = await workbench.call_tool(
        "taskmarket_list_tasks", {"status": "open", "limit": 5}
    )
```

Task creation is deliberately confirmation-gated. The application must first
review the exact `taskmarket_preview_task` result, provide an approval
callback, and pass `confirm=True` with the matching confirmation token. The
workbench performs a Base/USDC balance preflight and delegates the write to
the first-party CLI; it never accepts private keys, accepts or rejects
submissions, or retries an ambiguous write. Install the CLI separately only
when task creation is intentionally enabled:

```bash
npm install --global @lucid-agents/taskmarket
```
