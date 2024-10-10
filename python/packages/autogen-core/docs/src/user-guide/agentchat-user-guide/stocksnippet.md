``````{tab-set}

`````{tab-item} AgentChat (v0.4x)
```python
import asyncio
import logging
from autogen_agentchat import EVENT_LOGGER_NAME
from autogen_agentchat.agents import CodeExecutorAgent, CodingAssistantAgent
from autogen_agentchat.logging import ConsoleLogHandler
from autogen_agentchat.teams import RoundRobinGroupChat, StopMessageTermination
from autogen_core.components.code_executor import DockerCommandLineCodeExecutor
from autogen_core.components.models import OpenAIChatCompletionClient

logger = logging.getLogger(EVENT_LOGGER_NAME)
logger.addHandler(ConsoleLogHandler())
logger.setLevel(logging.INFO)

async def main() -> None:
    async with DockerCommandLineCodeExecutor(work_dir="coding") as code_executor:
        code_executor_agent = CodeExecutorAgent("code_executor", code_executor=code_executor)
        coding_assistant_agent = CodingAssistantAgent(
            "coding_assistant", model_client=OpenAIChatCompletionClient(model="gpt-4o", api_key="YOUR_API_KEY")
        )
        group_chat = RoundRobinGroupChat([coding_assistant_agent, code_executor_agent])
        result = await group_chat.run(
            task="Create a plot of NVDIA and TSLA stock returns YTD from 2024-01-01 and save it to 'nvidia_tesla_2024_ytd.png'.",
            termination_condition=StopMessageTermination(),
        )

asyncio.run(main())
```
`````

`````{tab-item} v0.2x
```python
from autogen.coding import DockerCommandLineCodeExecutor
from autogen import AssistantAgent, UserProxyAgent, config_list_from_json

llm_config = {"model": "gpt-4o", "api_type": "openai", "api_key": "YOUR_API_KEY"}
code_executor = DockerCommandLineCodeExecutor(work_dir="coding")
assistant = AssistantAgent("assistant", llm_config=llm_config)
code_executor_agent = UserProxyAgent(
    "code_executor_agent",
    code_execution_config={"executor": code_executor},
)
result = code_executor_agent.initiate_chat(
    assistant,
    message="Create a plot of NVIDIA and TESLA stock returns YTD from 2024-01-01 and save it to 'nvidia_tesla_2024_ytd.png'.",
)
code_executor.stop()
```
`````

``````
