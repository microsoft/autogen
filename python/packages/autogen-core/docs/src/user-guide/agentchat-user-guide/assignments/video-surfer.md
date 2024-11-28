## Video Surfer Using AutoGen

In this assignment, we will learn how to create a video surfing agent using AutoGen.
In particular, we will using AutoGen's higher-level API provided in the autogen_agentchat package.


### Step 1: Install AutoGen

First, you need to install AutoGen. You can install it using pip:

```bash
pip install autogen_agentchat
```


### Step 2: Run the Video Surfer Agent Template

Next, we will define a VideoSurferAgent that inherits from AssistantAgent. The VideoSurferAgent will be responsible for surfing videos.

TASK: Run the following script in your Python environment:

```python
from autogen_core.components.tools import Tool
from autogen_core.components.models import ChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from typing import List, Callable, Any, Awaitable


############################################################
############## Tools for VideoSuferAgent ###################
############################################################
"""
Python functions that will be used by the agent to perform actions.
Feel free to modify these functions to perform the real actions.
Or add more functions to perform more actions.
"""
def get_video_length(video_path: str) -> float:
    # Get the length of the video
    # Modify this function to get the real length of the video
    return 10.0

def get_video_transcription(video_path: str) -> str:
    # Get the transcription of the video
    # Modify this function to get the real transcription of the video
    return "This is a transcription of the video."

############################################################


class VideoSurferAgent(AssistantAgent):
    """
    Define a VideoSurferAgent that can answer questions about a local video.
    """
    def __init__(
        self,
        name: str,
        model_client: ChatCompletionClient,
        *,
        ### List of tools that the agent can use to perform actions
        ### Feel free to add more tools or modify the existing ones
        tools: List[Tool | Callable[..., Any] | Callable[..., Awaitable[Any]]] | None = [
            get_video_length
        ],
        description: str = "An agent that can answer questions about a local video.",
        system_message: str
        | None = """
You are a helpful agent that is an expert at answering questions from a video.
    
When asked to answer a question about a video, you should:
1. Check if that video is available locally.
2. Use the transcription to find which part of the video the question is referring to.
3. Optionally use screenshots from those timestamps
4. Provide a detailed answer to the question.
Reply with TERMINATE when the task has been completed.
"""
    ):
        super().__init__(name, model_client, tools=tools, description=description, system_message=system_message)


async def main() -> None:
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

In the above code, we define a VideoSurferAgent that inherits from AssistantAgent. The VideoSurferAgent is responsible for answering questions about a local video. Currently, the agent can get the length of the video using the get_video_length function. But the function always returns a fixed value of 10.0. 

TASK: Modify the get_video_length function to get the real length of the video. 

Similarly, the get_video_transcription function always returns a fixed transcription. 

TASK: Modify the get_video_transcription function to get the real transcription of the video.

### Step 3: Add More Actions

You can add more actions to the VideoSurferAgent by defining more functions in the tools list. For example, you can add a function to get the screenshots from the video at specific timestamps. Or functions that using multimodal AI models to caption a screenshot.

TASK: Add more functions to the tools list to perform more actions.

Remember to modify the tools list in the VideoSurferAgent constructor to include the new functions.