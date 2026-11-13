# KCP Benchmark Results

Benchmark comparing baseline (unguided file exploration) vs KCP-guided navigation across
8 common questions about the AutoGen framework. Each query was answered by a Claude
claude-haiku-4-5-20251001 agent using read, glob, and grep tools. Tool call count measures
retrieval efficiency — fewer calls means faster, cheaper answers.

## Results

| Query | Baseline | KCP | Saved |
|-------|----------|-----|-------|
| What is the difference between AutoGen Core and AgentChat? | 7 | 2 | 5 |
| How do I build my first multi-agent chat with AutoGen? | 9 | 2 | 7 |
| How do I add tools to an agent in AutoGen? | 23 | 2 | 21 |
| What design patterns does AutoGen support for multi-agent orchestration? | 32 | 4 | 28 |
| How do I implement group chat with multiple agents? | 12 | 3 | 9 |
| How do I add memory to an agent? | 24 | 2 | 22 |
| What LLM providers and model clients does AutoGen support? | 36 | 16 | 20 |
| How do I handle human-in-the-loop approval in AutoGen? | 25 | 2 | 23 |
| **TOTAL** | **168** | **33** | **135** |

## Summary

**80% reduction in tool calls** (168 baseline vs 33 KCP across 8 queries).

The KCP manifest allows agents to skip broad repo exploration and jump directly to the
relevant TL;DR or focused unit by matching query triggers. Most queries resolved in 2-4
tool calls instead of 12-36. The largest gains came from queries that would otherwise
trigger exhaustive directory scans — tools (23 → 2), memory (24 → 2), human-in-the-loop
(25 → 2), and design patterns (32 → 4). The model-clients query showed the smallest
reduction (36 → 16) because the target notebook is large and the agent needed multiple
reads to extract the full provider list, but still saved 20 calls vs baseline.
