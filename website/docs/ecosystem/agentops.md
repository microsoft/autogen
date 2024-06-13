# AgentOps 🖇️

![logo](https://raw.githubusercontent.com/AgentOps-AI/agentops/35d5682866921a9e28d8ef66ae3c3b3d92d8fa6b/img/logo.png)

[AgentOps](https://agentops.ai/?=autogen) provides session replays, metrics, and monitoring for agents.

At a high level, AgentOps gives you the ability to monitor LLM calls, costs, latency, agent failures, multi-agent interactions, tool usage, session-wide statistics, and more. For more info, check out the [AgentOps Repo](https://github.com/AgentOps-AI/agentops).

<details open>
  <summary>Agent Dashboard</summary>
  <a href="https://app.agentops.ai?ref=gh">
   <img src="https://github.com/AgentOps-AI/agentops/assets/14807319/158e082a-9a7d-49b7-9b41-51a49a1f7d3d" style="width: 90%;" alt="Agent Dashboard"/>
  </a>
</details>

<details>
  <summary>Session Analytics</summary>
  <a href="https://app.agentops.ai?ref=gh">
    <img src="https://github.com/AgentOps-AI/agentops/assets/14807319/d7228019-1488-40d3-852f-a61e998658ad" style="width: 90%;" alt="Session Analytics"/>
  </a>
</details>

<details>
  <summary>Session Replays</summary>
  <a href="https://app.agentops.ai?ref=gh">
    <img src="https://github.com/AgentOps-AI/agentops/assets/14807319/561d59f3-c441-4066-914b-f6cfe32a598c" style="width: 90%;" alt="Session Replays"/>
  </a>
</details>


## Installation

AgentOps works seamlessly with applications built using Autogen.

1. **Install AgentOps**
```bash
pip install agentops
```

2. **Create an API Key:**
Create a user API key here: [Create API Key](https://app.agentops.ai/account)

3. **Configure Your Environment:**
Add your API key to your environment variables

```
AGENTOPS_API_KEY=<YOUR_AGENTOPS_API_KEY>
```

4. **Initialize AgentOps**

To start tracking all available data on Autogen runs, simply add two lines of code before implementing Autogen.

```python
import agentops
agentops.init() # Or: agentops.init(api_key="your-api-key-here")
```

After initializing AgentOps, Autogen will now start automatically tracking your agent runs.

## Features

- **LLM Costs**: Track spend with foundation model providers
- **Replay Analytics**: Watch step-by-step agent execution graphs
- **Recursive Thought Detection**: Identify when agents fall into infinite loops
- **Custom Reporting:** Create custom analytics on agent performance
- **Analytics Dashboard:** Monitor high level statistics about agents in development and production
- **Public Model Testing**: Test your agents against benchmarks and leaderboards
- **Custom Tests:** Run your agents against domain specific tests
- **Time Travel Debugging**:  Save snapshots of session states to rewind and replay agent runs from chosen checkpoints.
- **Compliance and Security**: Create audit logs and detect potential threats such as profanity and PII leaks
- **Prompt Injection Detection**: Identify potential code injection and secret leaks

## Autogen + AgentOps examples
* [AgentChat with AgentOps Notebook](/docs/notebooks/agentchat_agentops)
* [More AgentOps Examples](https://docs.agentops.ai/v1/quickstart)

## Extra links

- [🐦 Twitter](https://twitter.com/agentopsai/)
- [📢 Discord](https://discord.gg/JHPt4C7r)
- [🖇️ AgentOps Dashboard](https://app.agentops.ai/ref?=autogen)
- [📙 Documentation](https://docs.agentops.ai/introduction)
