# Agent Memory with Zep

<img src="https://raw.githubusercontent.com/getzep/zep/refs/heads/main/assets/zep-logo-icon-gradient-rgb.svg?raw=true" style="width: 20%;" alt="Zep logo"/>

[Zep](https://www.getzep.com/?utm_source=autogen) is a long-term memory service for agentic applications used by both startups and enterprises. With Zep, you can build personalized, accurate, and production-ready agent applications.

Zep's memory continuously learns facts from interactions with users and your changing business data. With [just two API calls](https://help.getzep.com/memory?utm_source=autogen), you can persist chat history to Zep and recall facts relevant to the state of your agent.

Zep is powered by a temporal Knowledge Graph that allows reasoning with facts as they change. A combination of semantic and graph search enables accurate and low-latency fact retrieval.

Sign up for [Zep Cloud](https://www.getzep.com/?utm_source=autogen) or visit the [Zep Community Edition Repo](https://github.com/getzep/zep).

| Feature                                        | Description                                                                           |
| ---------------------------------------------- | ------------------------------------------------------------------------------------- |
| 💬 **Capture Detailed Conversational Context** | Zep's Knowledge Graph-based memory captures episodic, semantic, and temporal contexts |
| 🗄️ **Business Data is Context, too**           | Zep is able to extract facts from JSON and unstructured text as well                  |
| ⚙️ **Tailor For Your Business**                | Fact Ratings and other tools allow you to fine-tune retrieval for your use case       |
| ⚡️ **Instant Memory Retrieval**               | Retrieve relevant facts in under 100ms                                                |
| 🔐 **Compliance & Security**                   | User Privacy Management, SOC 2 Type II certification, and other controls              |
| 🖼️ **Framework Agnostic & Future-Proof**       | Use with AutoGen or any other framework, current or future                            |

<details>
  <summary><b><u>Zep Community Edition Walkthrough</u></b></summary>
  <a href="https://vimeo.com/1013045013">
  <img src="img/ecosystem-zep-ce-walkthrough.png" alt="Zep Fact Ratings" />
  </a>
</details>

<details open>
  <summary><b><u>User Chat Session and Facts</u></b></summary>
  <a href="https://help.getzep.com/chat-history-memory/facts?utm_source=autogen">
   <img src="img/ecosystem-zep-session.gif" style="width: 100%;" alt="Chat Session and Facts"/>
  </a>
</details>

<details>
  <summary><b><u>Implementating Fact Ratings</u></b></summary>
  <a href="https://vimeo.com/989192145">
  <img src="img/ecosystem-zep-fact-ratings.png" alt="Zep Fact Ratings" />
  </a>
</details>

## How Zep works

1. Add chat messages or data artifacts to Zep during each user interaction or agent event.
2. Zep intelligently integrates new information into the user's (or groups of users) Knowledge Graph, updating existing context as needed.
3. Retrieve relevant facts from Zep for subsequent interactions or events.

Zep's temporal Knowledge Graph maintains contextual information about facts, enabling reasoning about state changes and providing data provenance insights. Each fact includes `valid_at` and `invalid_at` dates, allowing agents to track changes in user preferences, traits, or environment.

## Zep is fast

Retrieving facts is simple and very fast. Unlike other memory solutions, Zep does not use agents to ensure facts are relevant. It precomputes facts, entity summaries, and other artifacts asynchronously. For on-premise use, retrieval speed primarily depends on your embedding service's performance.

## Zep supports many types of data

You can add a variety of data artifacts to Zep:

- Adding chat history messages.
- Ingestion of JSON and unstructured text.

Zep supports chat session, user, and group-level graphs. Group graphs allow for capturing organizational knowledge.

## Getting Started

### Zep Cloud

1. Sign up for [Zep Cloud](https://www.getzep.com?utm_source=autogen) and create a [Project API Key](https://help.getzep.com/projects?utm_source=autogen).

2. Install one of the [Zep Python, TypeScript or Go SDKs](https://help.getzep.com/sdks?utm_source=autogen). Python instructions shown below.

```shell
pip install zep-cloud
```

3. Initialize a client

```python
import os
from zep_cloud.client import AsyncZep

API_KEY = os.environ.get('ZEP_API_KEY')
client = AsyncZep(
    api_key=API_KEY,
)
```

3. Review the Zep and Autogen [notebook example](/docs/notebooks/agent_memory_using_zep) for agent-building best practices.

### Zep Community Edition

Follow the [Getting Started guide](https://help.getzep.com/ce/quickstart?utm_source=autogen) or visit the [GitHub Repo](https://github.com/getzep/zep?utm_source=autogen).

## Autogen + Zep examples

- [Autogen Agents with Zep Memory Notebook](/docs/notebooks/agent_memory_using_zep)

## Extra links

- [📙 Documentation](https://help.getzep.com/?utm_source=autogen)
- [🐦 Twitter / X](https://x.com/zep_ai/)
- [📢 Discord](https://discord.com/invite/W8Kw6bsgXQ)
