from typing import Any, Awaitable, Callable, List, Optional

from autogen_agentchat.agents import AssistantAgent
from autogen_core.components.models import ChatCompletionClient
from autogen_core.components.tools import Tool

from .tools import (
    extract_audio,
    get_screenshot_at,
    get_video_length,
    save_screenshot,
    transcribe_audio_with_timestamps,
    transcribe_video_screenshot,
)


class VideoSurfer(AssistantAgent):
    """
    VideoSurfer is a specialized agent designed to answer questions about a local video file.

    This agent utilizes various tools to extract information from the video, such as its length, screenshots at specific timestamps, and audio transcriptions. It processes these elements to provide detailed answers to user queries.

    Available tools:

    - :func:`~autogen_ext.agents.video_surfer.tools.extract_audio`
    - :func:`~autogen_ext.agents.video_surfer.tools.get_video_length`
    - :func:`~autogen_ext.agents.video_surfer.tools.transcribe_audio_with_timestamps`
    - :func:`~autogen_ext.agents.video_surfer.tools.get_screenshot_at`
    - :func:`~autogen_ext.agents.video_surfer.tools.save_screenshot`
    - :func:`~autogen_ext.agents.video_surfer.tools.transcribe_video_screenshot`

    Example usage:

        The following example demonstrates how to create an video surfing agent with
        a model client and generate a response to a simple query about a local video
        called video.mp4.

        .. code-block:: python


            import asyncio
            from autogen_agentchat.ui import Console
            from autogen_agentchat.conditions import TextMentionTermination
            from autogen_agentchat.teams import RoundRobinGroupChat
            from autogen_ext.models import OpenAIChatCompletionClient
            from autogen_ext.agents.video_surfer import VideoSurfer

            async def main() -> None:
                \"\"\"
                Main function to run the video agent.
                \"\"\"
                # Define an agent
                video_agent = VideoSurfer(
                    name="VideoSurfer",
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

        The following example demonstrates how to create and use a VideoSurfer and UserProxyAgent with MagenticOneGroupChat.

        .. code-block:: python

            import asyncio

            from autogen_agentchat.ui import Console
            from autogen_agentchat.teams import MagenticOneGroupChat
            from autogen_agentchat.agents import UserProxyAgent
            from autogen_ext.models import OpenAIChatCompletionClient
            from autogen_ext.agents.video_surfer import VideoSurfer

            async def main() -> None:
                \"\"\"
                Main function to run the video agent.
                \"\"\"

                model_client = OpenAIChatCompletionClient(model="gpt-4o-2024-08-06")

                # Define an agent
                video_agent = VideoSurfer(
                    name="VideoSurfer",
                    model_client=model_client
                    )

                web_surfer_agent = UserProxyAgent(
                    name="User"
                )

                # Define a team
                agent_team = MagenticOneGroupChat([web_surfer_agent, video_agent], model_client=model_client,)

                # Run the team and stream messages to the console
                stream = agent_team.run_stream(task="Find a latest video about magentic one on youtube and extract quotes from it that make sense.")
                await Console(stream)

            asyncio.run(main())
    """

    DEFAULT_DESCRIPTION = "An agent that can answer questions about a local video."

    DEFAULT_SYSTEM_MESSAGE = """
    You are a helpful agent that is an expert at answering questions from a video.
    When asked to answer a question about a video, you should:
    1. Check if that video is available locally.
    2. Use the transcription to find which part of the video the question is referring to.
    3. Optionally use screenshots from those timestamps
    4. Provide a detailed answer to the question.
    Reply with TERMINATE when the task has been completed.
    """

    def __init__(
        self,
        name: str,
        model_client: ChatCompletionClient,
        *,
        tools: List[Tool | Callable[..., Any] | Callable[..., Awaitable[Any]]] | None = None,
        description: Optional[str] = None,
        system_message: Optional[str] = None,
    ):
        """
        Initialize the VideoSurfer.

        Args:
            name (str): The name of the agent.
            model_client (ChatCompletionClient): The model client used for generating responses.
            tools (List[Tool | Callable[..., Any] | Callable[..., Awaitable[Any]]] | None, optional):
                A list of tools or functions the agent can use. If not provided, defaults to all video tools from the action space.
            description (str, optional): A brief description of the agent. Defaults to "An agent that can answer questions about a local video.".
            system_message (str | None, optional): The system message guiding the agent's behavior. Defaults to a predefined message.
        """
        super().__init__(
            name=name,
            model_client=model_client,
            tools=tools
            or [
                get_video_length,
                get_screenshot_at,
                save_screenshot,
                self.vs_transribe_video_screenshot,
                extract_audio,
                transcribe_audio_with_timestamps,
            ],
            description=description or self.DEFAULT_DESCRIPTION,
            system_message=system_message or self.DEFAULT_SYSTEM_MESSAGE,
        )

    async def vs_transribe_video_screenshot(self, video_path: str, timestamp: float) -> str:
        """
        Transcribes the video screenshot at a specific timestamp.

        Args:
            video_path (str): Path to the video file.
            timestamp (float): Timestamp to take the screenshot.

        Returns:
            str: Transcription of the video screenshot.
        """
        return await transcribe_video_screenshot(video_path, timestamp, self._model_client)
