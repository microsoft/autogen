import asyncio
import os
import yaml
from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_core.models import ModelFamily
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_agentchat.conditions import TextMentionTermination
from custom_code_executor import CustomCodeExecutorAgent
from autogen_core.models import ChatCompletionClient

async def main() -> None:

    # Load model configuration and create the model client.
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    model_client = ChatCompletionClient.load_component(config["model_config"])

    # Coder
    coder_agent = MagenticOneCoderAgent(
        name="coder",
        model_client=model_client,
    )

    # Executor
    executor = CustomCodeExecutorAgent(
        name="executor",
        code_executor=LocalCommandLineCodeExecutor(),
        sources=["coder"],
    )

    # Termination condition
    termination = TextMentionTermination(text="TERMINATE", sources=["executor"])

    # Define a team
    agent_team = RoundRobinGroupChat([coder_agent, executor], max_turns=12, termination_condition=termination)

    prompt = ""
    with open("prompt.txt", "rt") as fh:
        prompt = fh.read()

    task = f"""Complete the following python function. Format your output as Markdown python code block containing the entire function definition:

```python
{prompt}
```
"""

    # Run the team and stream messages to the console.
    stream = agent_team.run_stream(task=task)
    await Console(stream)

asyncio.run(main())
