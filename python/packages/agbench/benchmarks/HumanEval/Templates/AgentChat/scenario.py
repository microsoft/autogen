import asyncio
import os
import yaml
from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_core.models import ModelFamily
from autogen_core.model_context import UnboundedChatCompletionContext, ChatCompletionContext
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_agentchat.conditions import TextMentionTermination
from custom_code_executor import CustomCodeExecutorAgent
from reasoning_model_context import ReasoningModelContext
from autogen_core.models import ChatCompletionClient

async def main() -> None:

    # Load model configuration and create the model client.
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    model_client = ChatCompletionClient.load_component(config["model_config"])

    # Model context
    model_context : ChatCompletionContext
    if model_client.model_info["family"] == ModelFamily.R1:
        model_context = ReasoningModelContext()
    else:
        model_context = UnboundedChatCompletionContext()

    # Coder
    coder_agent = MagenticOneCoderAgent(
        name="coder",
        model_client=model_client,
    )
    # Set model context.
    coder_agent._model_context = model_context # type: ignore

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
