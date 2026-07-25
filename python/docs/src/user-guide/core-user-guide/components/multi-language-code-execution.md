---
myst:
  html_meta:
    "description lang=en": |
      Patterns for multi-language, repository-aware code execution backends in AutoGen.
---

# Multi-Language Code Execution

AutoGen code execution is not limited to a Python REPL. The safest default is still to run generated code in an isolated executor, but some applications need shell commands, Node.js scripts, Go programs, or tools that run with repository context. This page summarizes the supported patterns and the tradeoffs to consider before exposing an execution backend to an agent.

## Choose an Execution Pattern

Use {py:class}`~autogen_ext.code_executors.docker.DockerCommandLineCodeExecutor` when generated code can run in a disposable container. This is the recommended pattern for untrusted model-generated code because dependencies, files, and processes are isolated from the host.

Use {py:class}`~autogen_ext.code_executors.local.LocalCommandLineCodeExecutor` only when the agent must use host-local repository context, such as a checked-out source tree, local build tools, or project-specific virtual environments. Local execution can run any command the current user can run, so pair it with human approval, a restricted working directory, and short timeouts.

Use {py:class}`~autogen_ext.tools.mcp.McpWorkbench` when code execution is provided by an MCP server. This is useful when different clients or model providers should share the same execution backend through a standard tool interface.

## Multi-Language Command Blocks

Command-line executors receive {py:class}`~autogen_core.code_executor.CodeBlock` values. The `language` field tells the executor how to route the block. For example, an application may accept Python, shell, JavaScript, or Go blocks and send them to the same executor interface while keeping execution policy in one place.

```python
from autogen_core.code_executor import CodeBlock

blocks = [
    CodeBlock(code="python --version", language="sh"),
    CodeBlock(code="node --version", language="sh"),
    CodeBlock(code="go test ./...", language="sh"),
]
```

Keep the set of accepted languages explicit. If a workflow only needs shell and Python, reject other language labels before they reach the executor.

## Repository-Aware Execution

Repository-aware execution is useful for coding agents, test repair, and documentation checks. Prefer this setup:

- Set `work_dir` to a dedicated checkout or temporary copy of the repository.
- Run with the least-privileged user available.
- Require approval before commands that write outside `work_dir`, install dependencies globally, start long-running services, or access secrets.
- Use executor timeouts and cancellation tokens for every run.
- Persist stdout, stderr, exit code, and the command language as the execution record.

Local repository access is powerful, but it is not a sandbox. Use Docker or another isolated service whenever the agent does not need host-local state.

## MCP Execution Backend

An MCP server can expose execution as one or more tools, such as `run_python`, `run_shell`, or `run_tests`. AutoGen agents can call those tools through {py:class}`~autogen_ext.tools.mcp.McpWorkbench`.

```python
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams

server_params = StdioServerParams(
    command="python",
    args=["-m", "my_execution_server"],
)

async def main() -> None:
    async with McpWorkbench(server_params) as workbench:
        agent = AssistantAgent(
            name="coding_agent",
            model_client=OpenAIChatCompletionClient(model="gpt-4.1"),
            workbench=workbench,
        )
        await agent.run(task="Check the repository tests")
```

Keep policy in the MCP server as well as in the AutoGen application. The server should validate the working directory, allowed commands, timeouts, and environment variables instead of trusting tool arguments from the model.

## Production Checklist

- Prefer isolated execution for untrusted code.
- Make language allow-lists explicit.
- Use short timeouts and cancellation for every command.
- Capture stdout, stderr, exit code, language, and working directory.
- Avoid passing secrets into the execution environment.
- Require human approval for host-local writes, dependency installation, network access, and long-running processes.
- Treat MCP tool outputs as untrusted data when they are inserted back into model context.

See [Command Line Code Executors](./command-line-code-executors.ipynb) for built-in Docker and local executor examples, and [Workbench](./workbench.ipynb) for MCP workbench setup.
