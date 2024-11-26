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