# AgentChat Synap Memory

This sample shows how to give an AutoGen `AssistantAgent` persistent, cross-session memory via [Synap](https://maximem.ai) — a managed long-term memory layer for AI agents.

## Setup

```bash
pip install maximem-synap-autogen maximem-synap "autogen-agentchat" "autogen-ext[openai]"
```

Set environment variables:

```bash
export SYNAP_API_KEY=<your-key>     # get one free at https://synap.maximem.ai
export OPENAI_API_KEY=<your-key>
```

## Run

```bash
python main.py
```

The agent is wired with `SynapSearchTool` and `SynapStoreTool` — it can semantically search the user's existing memories and persist new facts the user mentions. Memories are scoped to the `user_id` and `customer_id` you provide, so they persist across conversation runs.

## Resources

- [Synap documentation](https://docs.maximem.ai)
- [PyPI: `maximem-synap-autogen`](https://pypi.org/project/maximem-synap-autogen/)
- [Open source integration package](https://github.com/maximem-ai/maximem_synap_sdk/tree/main/packages/integrations/synap-autogen)
