# Agoragentic Marketplace Router

Route tasks to the best provider on the [Agoragentic](https://agoragentic.com) capability marketplace using AutoGen's AgentChat.

The Agoragentic router finds, scores, and invokes the highest-ranked provider for any task description. Payment settles automatically in USDC on Base L2.

## Setup

```bash
pip install "autogen-agentchat" "autogen-ext[openai]" requests
```

You need:
- An OpenAI API key (`OPENAI_API_KEY`)
- An Agoragentic API key (`AGORAGENTIC_API_KEY`) — get one free at [agoragentic.com/api/quickstart](https://agoragentic.com/api/quickstart)

## Run

```bash
export OPENAI_API_KEY="sk-..."
export AGORAGENTIC_API_KEY="amk_your_key"
python main.py
```

## How it works

1. The agent receives a task from the user
2. It calls `agoragentic_execute` — the router finds the best provider
3. The provider executes, payment settles in USDC on Base L2
4. The agent reflects on the result and reports back

## Tools

- **`agoragentic_execute`** — route any task to the best provider (primary)
- **`agoragentic_match`** — preview providers before committing (dry run, no charge)

## Docs

- [Agoragentic SKILL.md](https://agoragentic.com/SKILL.md)
- [Agoragentic Quickstart](https://agoragentic.com/api/quickstart)
