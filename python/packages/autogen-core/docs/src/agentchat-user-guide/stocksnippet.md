``````{tab-set}

`````{tab-item} AgentChat (v0.4x)
```python
from autogen_agentchat.agents import CodeExecutorAgent, CodingAssistantAgent
from autogen_agentchat.teams.group_chat import RoundRobinGroupChat
from autogen_core.components.code_executor import DockerCommandLineCodeExecutor
from autogen_core.components.models import OpenAIChatCompletionClient

async with DockerCommandLineCodeExecutor(work_dir="coding") as code_executor:
    code_executor_agent = CodeExecutorAgent("code_executor", code_executor=code_executor)
    coding_assistant_agent = CodingAssistantAgent(
        "coding_assistant", model_client=OpenAIChatCompletionClient(model="gpt-4")
    )
    group_chat = RoundRobinGroupChat([coding_assistant_agent, code_executor_agent])
    result = await group_chat.run(
        task="Create a plot of NVIDIA and TESLA stock returns YTD from 2024-01-01 and save it to 'nvidia_tesla_2024_ytd.png'."
    )
    print(result)
```
`````

`````{tab-item} v0.2x
```python
from autogen import AssistantAgent, UserProxyAgent, config_list_from_json

config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")
assistant = AssistantAgent("assistant", llm_config={"config_list": config_list})
code_executor_agent = UserProxyAgent(
    "code_executor_agent",
    code_execution_config={"work_dir": "coding", "use_docker": True}
)
code_executor_agent.initiate_chat(
    assistant,
    message="Create a plot of NVIDIA and TESLA stock returns YTD from 2024-01-01 and save it to 'nvidia_tesla_2024_ytd.png'."
)
```
`````

``````
