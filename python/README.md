# AutoGen Python Development Guide

[![Docs (dev)](https://img.shields.io/badge/Docs-dev-blue)](https://microsoft.github.io/autogen/dev/)
[![Docs (latest release)](https://img.shields.io/badge/Docs-latest%20release-blue)](https://microsoft.github.io/autogen/dev/)
[![PyPi autogen-core](https://img.shields.io/badge/PyPi-autogen--core-blue?logo=pypi)](https://pypi.org/project/autogen-core/) [![PyPi autogen-agentchat](https://img.shields.io/badge/PyPi-autogen--agentchat-blue?logo=pypi)](https://pypi.org/project/autogen-agentchat/) [![PyPi autogen-ext](https://img.shields.io/badge/PyPi-autogen--ext-blue?logo=pypi)](https://pypi.org/project/autogen-ext/)

This directory works as a single `uv` workspace containing all project packages, including:

- `packages/autogen-core`: interface definitions and reference implementations of agent runtime, model, tool, workbench, memory, tracing.
- `packages/autogen-agentchat`: single and multi-agent workflows built on top of `autogen-core`.
- `packages/autogen-ext`: implementations for ecosystem integrations. For example, `autogen-ext[openai]` provides the OpenAI model client.
- `packages/autogen-studio`: a web-based IDE for building and running AutoGen agents.

## Migrating from 0.2.x?

Please refer to the [migration guide](./migration_guide.md) for how to migrate your code from 0.2.x to 0.4.x.

## Quick Start

**TL;DR**, run all checks with:

```sh
uv sync --all-extras
source .venv/bin/activate
poe check
```

## Setup

`uv` is a package manager that assists in creating the necessary environment and installing packages to run AutoGen.

- [Install `uv`](https://docs.astral.sh/uv/getting-started/installation/).

To upgrade `uv` to the latest version, run:

```sh
uv self update
```

## Virtual Environment

During development, you may need to test changes made to any of the packages.\
To do so, create a virtual environment where the AutoGen packages are installed based on the current state of the directory.\
Run the following commands at the root level of the Python directory:

```sh
uv sync --all-extras
source .venv/bin/activate
```

- `uv sync --all-extras` will create a `.venv` directory at the current level and install packages from the current directory along with any other dependencies. The `all-extras` flag adds optional dependencies.
- `source .venv/bin/activate` activates the virtual environment.

## Common Tasks

To create a pull request (PR), ensure the following checks are met. You can run each check individually:

- Format: `poe format`
- Lint: `poe lint`
- Test: `poe test`
- Mypy: `poe mypy`
- Pyright: `poe pyright`
- Build docs: `poe docs-build`
- Check docs: `poe docs-check`
- Clean docs: `poe docs-clean`
- Check code blocks in API references: `poe docs-check-examples`
- Auto rebuild+serve docs: `poe docs-serve`
- Check samples in `python/samples`: `poe samples-code-check`
  Alternatively, you can run all the checks with:
- `poe check`

> [!NOTE]
> These need to be run in the virtual environment.

## Syncing Dependencies

When you pull new changes, you may need to update the dependencies.
To do so, first make sure you are in the virtual environment, and then in the `python` directory, run:

```sh
uv sync --all-extras
```

This will update the dependencies in the virtual environment.

## Building Documentation

The documentation source directory is located at `docs/src/`.

To build the documentation, run this from the root of the Python directory:

```sh
poe docs-build
```

To serve the documentation locally, run:

```sh
poe docs-serve
```

When you make changes to the doc strings or add new modules, you may need to
refresh the API references in the documentation by first cleaning the docs and
then building them again:

```sh
poe docs-clean # This will remove the build directory and the reference directory
poe docs-build # This will rebuild the documentation from scratch
```

## Writing Documentation

When you add a new public class or function, you should always add a docstring
to it. The docstring should follow the
[Google style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) layout
and the Sphinx RST format for Python docstrings.

The docstring for a public class or function should include:

- A short description of the class or function at the beginning immediately after the `"""`.
- A longer description if necessary, explaining the purpose and usage.
- A list of arguments with their types and descriptions, using the `Args` section.
  Each argument should be listed with its name, type, and a brief description.
- A description of the return value and its type, using the `Returns` section.
  If the function does not return anything, you can omit this section.
- A list of exceptions that the function may raise, with descriptions,
  using the `Raises` section. This is optional but recommended if the function can raise exceptions that users should be aware of.
- Examples of how to use the class or function, using the `Examples` section,
  and formatted using `.. code-block:: python` directive. Optionally, also include the output of the example using
  `.. code-block:: text` directive.

Here is an example of a docstring for `McpWorkbench` class:

```python
class McpWorkbench(Workbench, Component[McpWorkbenchConfig]):
    """A workbench that wraps an MCP server and provides an interface
    to list and call tools provided by the server.

    This workbench should be used as a context manager to ensure proper
    initialization and cleanup of the underlying MCP session.

    Args:
        server_params (McpServerParams): The parameters to connect to the MCP server.
            This can be either a :class:`StdioServerParams` or :class:`SseServerParams`.
        tool_overrides (Optional[Dict[str, ToolOverride]]): Optional mapping of original tool
            names to override configurations for name and/or description. This allows
            customizing how server tools appear to consumers while maintaining the underlying
            tool functionality.

    Raises:
        ValueError: If there are conflicts in tool override names.

    Examples:

        Here is a simple example of how to use the workbench with a `mcp-server-fetch` server:

        .. code-block:: python

            import asyncio

            from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams


            async def main() -> None:
                params = StdioServerParams(
                    command="uvx",
                    args=["mcp-server-fetch"],
                    read_timeout_seconds=60,
                )

                # You can also use `start()` and `stop()` to manage the session.
                async with McpWorkbench(server_params=params) as workbench:
                    tools = await workbench.list_tools()
                    print(tools)
                    result = await workbench.call_tool(tools[0]["name"], {"url": "https://github.com/"})
                    print(result)


            asyncio.run(main())
```

The code blocks with `.. code-block:: python` is checked by the `docs-check-examples` task using Pyright,
so make sure the code is valid. Running the code as a script and checking it using `pyright`
is a good way to ensure the code examples are correct.

When you reference a class, method, or function in the docstring, you should always
use the `:class:`, `:meth:`, or `:func:` directive to create a link to the class or function.
Always use the fully qualified name of the class or function, including the package name, but
prefix it with a `~` for shorter rendering in the documentation.
For example, if you are referencing the `AssistantAgent` class in the `autogen-agentchat` package,
you should write it as `:class:~autogen_agentchat.AssistantAgent`.

For a public data class, including those that are Pydantic models, you should also include docstrings
for each field in the class.

## Writing Tests

When you add a new public class or function, you should also always add tests for it.
We track test coverage and aim for not reducing the coverage percentage with new changes.

We use `pytest` for testing, and you should always use fixtures to set up the test dependencies.

Use mock objects to simulate dependencies and avoid making real API calls or database queries in tests.
See existing tests for examples of how to use fixtures and mocks.

For model clients, use `autogen_ext.models.replay.ReplayChatCompletionClient` as a
drop-in replacement for the model client to simulate responses without making real API calls.

When certain tests requires interaction with actual model APIs or other external services,
you should configure the tests to be skipped if the required services are not available.
For example, if you are testing a model client that requires an OpenAI API key,
you can use the `pytest.mark.skipif` decorator to skip the test if the environment variable for the API key is not set.

## Creating a New Package

To create a new package, similar to `autogen-core` or `autogen-chat`, use the following:

```sh
uv sync --python 3.12
source .venv/bin/activate
cookiecutter ./templates/new-package/
```

- selector_group_chat_example.py: Example usage of SelectorGroupChat for web search and data analysis
- selector_group_chat_README.md: Overview and explanation of SelectorGroupChat, usage steps, and example scenario
- selector_group_chat_workflow.md: Workflow, termination conditions, and selector prompt details for SelectorGroupChat
- selector_group_chat_streaming_example.py: Streaming example for SelectorGroupChat with NBA player analysis task
- selector_group_chat_custom_selection_example.py: Custom selector_func and candidate_func examples for SelectorGroupChat
- selector_group_chat_advanced_example.py: Advanced customization examples for SelectorGroupChat (custom selector_func, candidate_func, UserProxyAgent, reasoning model)
- swarm_customer_support_example.py: Swarm team customer support (flights refund) example
- swarm_stock_research_example.py: Swarm team stock research example
- magentic_one_example.py: Magentic-One multi-agent orchestration examples (minimal, agents, helper class)
- graphflow_example.py: GraphFlow multi-agent workflow examples (sequential, parallel)
- graphflow_message_filtering_example.py: GraphFlow message filtering and advanced workflow examples
- graphflow_advanced_activation_example.py: GraphFlow advanced cycles and activation group examples
- listmemory_rag_example.py: ListMemory and RAG-style context example for AssistantAgent (simple, user preferences, context-aware responses)
- custom_chromadb_memory_example.py: ChromaDB vector memory store with AssistantAgent (vector DB, embedding, context-aware responses)
- custom_redis_memory_example.py: Redis vector memory store with AssistantAgent (persistent, context-aware responses)
- logging_example.py: Enabling and using trace and structured logging in AutoGen AgentChat (with custom handler and event example)
- tracing_observability_example.py: OpenTelemetry tracing and observability for AgentChat teams (Jaeger, OTLP, team execution tracing)
- travel_planning_example.py: Multi-agent travel planning system (planner, local, language, summary agents, collaborative itinerary)
- core_quickstart_example.py: Core agent runtime quick start (Modifier and Checker agents, SingleThreadedAgentRuntime, message passing)
- core_application_stack_example.py: Application stack, agent identity, lifecycle, topics, and type-based subscription patterns (Coder, Executor, Reviewer agents, message protocol)
- [Core Agent and Runtime Example](core_agent_and_runtime_example.py): Foundational example of agents, agent runtime, messages, direct messaging, broadcast, and type-based routing/subscription.
- [Core Application Stack Example](core_application_stack_example.py): Demonstrates agent identity, lifecycle, topics, and type-based subscription patterns with Coder, Executor, and Reviewer agents.
- [Core Logging Example](core_logging_example.py): Demonstrates trace and structured logging, custom structured events, and emitting logs from child loggers.
- [Core Model Clients Example](core_model_clients_example.py): Demonstrates usage of model clients (OpenAI, streaming, structured output, caching, agent integration) and model call logging.
- [Core Model Context Example](core_model_context_example.py): Demonstrates model context for message history and agent memory using BufferedChatCompletionContext.
- [Core Model Clients Example](core_model_clients_example.py): Demonstrates usage of model clients (OpenAI, streaming, structured output, caching, agent integration) and model call logging.
- [Core Logging Example](core_logging_example.py): Demonstrates trace and structured logging, custom structured events, and emitting logs from child loggers.
- [Core Agent and Runtime Example](core_agent_and_runtime_example.py): Foundational example of agents, agent runtime, messages, direct messaging, broadcast, and type-based routing/subscription.
- [Core Application Stack Example](core_application_stack_example.py): Demonstrates agent identity, lifecycle, topics, and type-based subscription patterns with Coder, Executor, and Reviewer agents.
- [Core Multi-Agent Patterns Example](core_multiagent_patterns_example.py): Demonstrates concurrent agent patterns: pub/sub, topic routing, result collection, and direct messaging.
- [Core Sequential Workflow Example](core_sequential_workflow_example.py): Sequential multi-agent workflow (Concept Extractor → Writer → Format & Proof → User)
- core_group_chat_example.py: Group chat multi-agent workflow (Writer, Illustrator, Editor, User, Manager)
- core_mixture_of_agents_example.py: Mixture of Agents pattern (multi-layer, feed-forward, orchestrator + workers)
- [core_multi_agent_debate_example.py](core_multi_agent_debate_example.py): Multi-Agent Debate pattern (sparse topology, solver/aggregator, GSM8K math problem)
- [core_reflection_example.py](core_reflection_example.py): Reflection pattern (coder/reviewer agents, iterative code generation and critique)
- [core_azure_openai_aad_termination_example.py](core_azure_openai_aad_termination_example.py): Azure OpenAI with AAD Auth, termination/intervention handler
- [core_langgraph_tool_use_agent_example.py](core_langgraph_tool_use_agent_example.py): LangGraph-backed agent with tool use
- [core_llamaindex_agent_example.py](core_llamaindex_agent_example.py): LlamaIndex-backed agent with Wikipedia tool
- [core_structured_output_gpt4o_example.py](core_structured_output_gpt4o_example.py): Structured output with GPT-4o models and usage tracking
