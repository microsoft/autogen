# VideoSurferAgent

The `VideoSurferAgent` is a specialized agent designed to answer questions about videos by utilizing various tools such as transcription, screenshots, and more.

## Installation

```bash
pip install autogen_ext[video_surfer]==<version>
```

## How to Use

Below is an example of how to use the `VideoSurferAgent` in a Python script.

```python
import asyncio
from autogen_agentchat.task import Console, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models import OpenAIChatCompletionClient
from autogen_ext.agents.video_surfer import VideoSurferAgent

async def main() -> None:
    """
    Main function to run the video agent.
    """
    # Define an agent
    video_agent = VideoSurferAgent(
        name="VideoSurferAgent",
        model_client=OpenAIChatCompletionClient(model="gpt-4o-2024-08-06")
    )

    # Define termination condition
    termination = TextMentionTermination("TERMINATE")

    # Define a team
    agent_team = RoundRobinGroupChat([video_agent], termination_condition=termination)

    # Run the team and stream messages to the console
    stream = agent_team.run_stream(task="How does Adam define complex tasks in video.mp4? What concrete example of complex does his use? Can you save this example to disk as well?")
    await Console(stream)

asyncio.run(main())
```

## Advanced Example

Below is an advanced example of how to use the `VideoSurferAgent` along with `MultimodalWebSurfer` in a Python script.

```python
import asyncio

from autogen_agentchat.task import Console
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_ext.models import OpenAIChatCompletionClient
from autogen_ext.agents.video_surfer import VideoSurferAgent
from autogen_ext.agents.web_surfer import MultimodalWebSurfer


async def main() -> None:
    """
    Main function to run the video agent.
    """

    model_client = OpenAIChatCompletionClient(model="gpt-4o-2024-08-06")

    # Define an agent
    video_agent = VideoSurferAgent(
        name="VideoSurferAgent",
        model_client=model_client
        )
    
    web_surfer_agent = MultimodalWebSurfer(
        name="WebSurferAgent",
        model_client=model_client
    )
    
    # Define a team
    agent_team = MagenticOneGroupChat([web_surfer_agent, video_agent], model_client=model_client,)

    # Run the team and stream messages to the console
    stream = agent_team.run_stream(task="Find a latest video about magentic one on youtube and extract quotes from it that make sense.")
    await Console(stream)

asyncio.run(main())
```