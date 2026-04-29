# Perplexity (experimental)

[Perplexity](https://docs.perplexity.ai) provides LLM chat completions and a
real-time web search API. AutoGen ships two components for it in
`autogen_ext`:

- {py:class}`~autogen_ext.models.perplexity.PerplexityChatCompletionClient` —
  a chat-completion client (Perplexity's `/v1/chat/completions` endpoint is
  OpenAI-compatible, so this client is a thin wrapper around
  {py:class}`~autogen_ext.models.openai.OpenAIChatCompletionClient`).
- {py:class}`~autogen_ext.tools.perplexity.PerplexitySearchTool` — a `BaseTool`
  that calls the
  [Perplexity Search API](https://docs.perplexity.ai/docs/search/quickstart)
  for ranked web results.

Install the extra:

```bash
pip install -U "autogen-ext[perplexity]"
```

Both components read the API key from the `api_key` argument, falling back
to the `PERPLEXITY_API_KEY` environment variable (or the `PPLX_API_KEY`
alias). Get a key from <https://www.perplexity.ai/account/api/keys>.

## Chat completion client

```python
import asyncio
from autogen_core.models import UserMessage
from autogen_ext.models.perplexity import PerplexityChatCompletionClient


async def main() -> None:
    client = PerplexityChatCompletionClient(model="sonar")
    result = await client.create(
        [UserMessage(content="What changed in Python 3.13?", source="user")]
    )
    print(result.content)
    await client.close()


asyncio.run(main())
```

See the [Perplexity Agent API quickstart](https://docs.perplexity.ai/docs/agent/quickstart)
for the list of available models.

## Search tool

```python
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.perplexity import PerplexitySearchTool


async def main() -> None:
    model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")
    search = PerplexitySearchTool()
    agent = AssistantAgent("researcher", model_client=model_client, tools=[search])
    result = await agent.run(task="Summarize today's top AI news with sources.")
    print(result.messages[-1].content)


asyncio.run(main())
```

The tool accepts `query`, `max_results`, `search_domain_filter`
(allow- or deny-list — prefix a domain with `-` to exclude; do **not** mix
allow and deny in the same call), and `search_recency_filter`
(`hour` / `day` / `week` / `month` / `year`). See
[domain filters](https://docs.perplexity.ai/docs/search/filters/domain-filter)
and [date/recency filters](https://docs.perplexity.ai/docs/search/filters/date-time-filters)
for details.
