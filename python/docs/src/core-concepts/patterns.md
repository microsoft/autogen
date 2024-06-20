# Multi-Agent Patterns

Agents can work together in a variety of ways to solve problems.
Research works like [AutoGen](https://aka.ms/autogen-paper),
[MetaGPT](https://arxiv.org/abs/2308.00352)
and [ChatDev](https://arxiv.org/abs/2307.07924) have shown
multi-agent systems out-performing single agent systems at complex tasks
like software development.

You can implement any multi-agent pattern using AGNext agents, which
communicate with each other using messages through the agent runtime
(see {doc}`/core-concepts/runtime` and {doc}`/core-concepts/agent`).
To make life easier, AGNext provides built-in patterns
in {py:mod}`agnext.chat.patterns` that you can use to build
multi-agent systems quickly.

To read about the built-in patterns, see the following guides:

1. {doc}`/guides/group-chat-coder-reviewer`
