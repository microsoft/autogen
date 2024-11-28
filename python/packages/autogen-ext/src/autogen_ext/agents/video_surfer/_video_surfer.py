from autogen_core.components.tools import Tool
from autogen_core.components.models import ChatCompletionClient

from autogen_agentchat.agents import AssistantAgent
from typing import List, Callable, Any, Awaitable

from ._action_space import extract_audio, get_video_length, transcribe_audio_with_timestamps, get_screenshot_at, save_screenshot, openai_transcribe_video_screenshot


class VideoSurferAgent(AssistantAgent):
    """
    VideoSurferAgent is a specialized agent designed to answer questions about a local video file.

    This agent utilizes various tools to extract information from the video, such as its length, screenshots at specific timestamps, and audio transcriptions. It processes these elements to provide detailed answers to user queries.

    Example usage:

        The following example demonstrates how to create an video surfing agent with
        a model client and generate a response to a simple query about a local video 
        called video.mp4.
    
        .. code-block:: python


            import asyncio
            from autogen_agentchat.task import Console, TextMentionTermination
            from autogen_agentchat.teams import RoundRobinGroupChat
            from autogen_ext.models import OpenAIChatCompletionClient
            from autogen_ext.agents.video_surfer import VideoSurferAgent

            async def main() -> None:
                \"\"\"
                Main function to run the video agent.
                \"\"\"
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
    """
    def __init__(
        self,
        name: str,
        model_client: ChatCompletionClient,
        *,
        tools: List[Tool | Callable[..., Any] | Callable[..., Awaitable[Any]]] | None = None,
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
        super().__init__(
            name=name,
            model_client=model_client,
            tools=tools or [
                get_video_length,
                get_screenshot_at,
                save_screenshot,
                openai_transcribe_video_screenshot,
                extract_audio,
                transcribe_audio_with_timestamps,
            ],
            description=description,
            system_message=system_message,
        )
