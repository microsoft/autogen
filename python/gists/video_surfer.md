# Tutorial: Video Surfer Agent using AutoGen

In this tutorial you'll learn how to create _video surfer agent_ using AutoGen.
We'll first walk you through how to create your development environment and then we'll extend
built-in agents in AutoGen and adapt them to create the video surfer.

## What you'll learn

- How to setup and install AutoGen.
- How to use and modify built-in agents provided by AutoGen.
- How to equip an agent with tools.
- How to create and use a multi-agent team to solve tasks.

## Requirements and resources

You'll need:

- Linux, Mac, or Windows machine with Python 3.10 or above
- An OpenAI API key

While this exercise is designed to be self-sufficient, at any time feel free to consult the [source code](https://aka.ms/autogen-gh) or the [documentation](https://microsoft.github.io/autogen/dev/).

## Install the dependencies

Create a python virtual environment. Please feel free to use a virtual environment manager of your choice (e.g., `venv` or `conda`). Once you have created the virtual environment, please install the `agentchat` package using:

```bash
pip install 'autogen-agentchat==0.4.0.dev8' 'autogen-ext==0.4.0.dev8'
```

This will install the high-level API for agents built using `autogen-core`.

## A hello world example with `AssistantAgent`

Run the script below. You'll need an OpenAI API key.

```python
import asyncio

from autogen_agentchat.task import Console, TextMentionTermination
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models import OpenAIChatCompletionClient


async def main() -> None:
    """
    Main function to run the video agent.
    """
    # Define an agent
    video_agent = AssistantAgent(
        name="VideoSurferAgent",
        model_client=OpenAIChatCompletionClient(
          model="gpt-4o",
          # api_key = "your_openai_api_key"
          )
        )

    # Define termination condition
    termination = TextMentionTermination("TERMINATE")

    # Define a team
    agent_team = RoundRobinGroupChat([video_agent], termination_condition=termination)

    # Run the team and stream messages to the console
    stream = agent_team.run_stream(task="Hi!")
    await Console(stream)

asyncio.run(main())
```

Note that AutoGen uses the Python async API. Here is a link to [async programming in python](https://docs.python.org/3/library/asyncio.html).

### Exercise 1: Modify the system message

Modify the system message to describe your video surfer agent's roles and responsibilities.

```python
  ...
  SYSTEM_MESSAGE="custom system message"
  video_agent = AssistantAgent(
        name="VideoSurferAgent",
        model_client=OpenAIChatCompletionClient(
          model="gpt-4o",
          # api_key = "your_openai_api_key"
          ),
        system_message=SYSTEM_MESSAGE
        )
  ...
```

### Exercise 2: Add a new action

Give your video surfer agent tools that can be used to perform specific actions. In this case, add an action that allows the video surfer to compute the length of a video.

```python

def get_video_length(video_path: str) -> str:
    """
    Returns the length of the video in seconds.

    :param video_path: Path to the video file.
    :return: Duration of the video in seconds.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Cannot open video file {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = frame_count / fps
    cap.release()

    return f"The video is {duration:.2f} seconds long."


  ...
  SYSTEM_MESSAGE="custom system message"
  video_agent = AssistantAgent(
      name="VideoSurferAgent",
      model_client=OpenAIChatCompletionClient(
        model="gpt-4o",
        # api_key = "your_openai_api_key"
        ),
      system_message=SYSTEM_MESSAGE,
      tools=[get_video_length],
   )
  ...

```

### Exercise 3: Add more actions of your choice

Now add any other tools of your choice. For example, you can try adding a tool that allows video surfer to transcribe the audio in the video, or a tool that allows the video surfer to caption the contents of the video a given timestamp. 

Note that if your tools require new dependecies (e.g., python packages) ensure that you've installed them.

```python

def tool1(...)
    ...


def tool2(...)
    ...

    ...
    tools=[get_video_length, tool1, tool2, ...],
    ...
```

### Exercise 4: Create an agent team

Now create a multi-agent team consisting of the a user (using the UserProxyAgent) and the MagenticOneGroupChat, a powerful agent that orchestrates other agents and solve tasks by planning and tracking progress via ledgers.

```python
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.agents import UserProxyAgent

async def main() -> None:
    """
    Main function to run the video agent.
    """

    # Define an agent
    video_agent = AssistantAgent(
        ...  # your arguments
        )

    user_proxy_agent = UserProxyAgent(
        name="User"
    )

    # Define a team
    agent_team = MagenticOneGroupChat([user_proxy_agent, video_agent], model_client=model_client,)

    # Run the team and stream messages to the console
    stream = agent_team.run_stream(task="Answer any questions the user asks about video.mp4.")
    await Console(stream)

asyncio.run(main())
```

Using your implementation check if you can answer the following questions:

- What is a high-level two sentence summary of the video?
- What is the motivation behind the project?
- How did they evaluate the success of their approach?

## Whats next?

- You are welcome to continue extending the video surfer for your needs. Add additional actions, or even pair it up with other agents to create an even powerful multi-agent team.
- Share your work! Record screenshots or videos of your video surfer in action and tweet! You may also upload your solution to GitHub! Make sure to use #AutoGen hashtag and tag @pyautogen so that we can discover your work!

## Need help?

You can check [VideoSurfer](https://github.com/microsoft/autogen/blob/c02d87e9cf90f4fd91da6b641f1de8077edb54db/python/packages/autogen-ext/src/autogen_ext/agents/video_surfer/_video_surfer.py) implementation to learn what else is possible!
