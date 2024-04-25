# AgentOps

> Create an account at [AgentOps.ai](https://agentops.ai/)

AgentOps works seamlessly with applications built using Autogen.

Install AgentOps with
```bash
pip install pyautogen[agentops]
```

To start tracking all available data on Autogen runs, simply add two lines of code before implementing Autogen.

```python
import agentops
agentops.init() # AgentOps API key named AGENTOPS_API_KEY in environment 
# or
agentops.init(api_key='you-api-key')
```

After initializing AgentOps, Autogen will now start automatically tracking
- LLM calls
- Agent names and actions
- Tool usage
- Correspondence between agents
- Errors
- Token usage and costs

### Example Implementation
[AgentOps-Notebook](../../../notebook/agentchat_agentops.ipynb)
[AgentOps Documentation](https://docs.agentops.ai/v1/quickstart)
