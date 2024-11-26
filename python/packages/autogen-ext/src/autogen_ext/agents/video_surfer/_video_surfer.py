from autogen_agentchat.agents import AssistantAgent

from ._action_space import extract_audio, get_video_length, transcribe_audio_with_timestamps, get_screenshot_at, save_screenshot, openai_transcribe_video_screenshot


class VideoSurferAgent(AssistantAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args,
                        **kwargs,
                        tools=[
                            get_video_length,
                            get_screenshot_at,
                            save_screenshot,
                            openai_transcribe_video_screenshot,
                            extract_audio,
                            transcribe_audio_with_timestamps,
                        ],
                        system_message = """
You are a helpful agent that is an expert at answering questions from videos.
    
When asked to answer a question about a video, you should:
1. Use the transcription to find which part of the video the question is referring to.
2. Optionally use screenshots from those timestamps
3. Provide a detailed answer to the question.
Reply with TERMINATE when the task has been completed.
"""
        )

# async def main() -> None:
#     """
#     Main function to run the video agent.
#     """
#     # Define an agent
#     video_agent = AssistantAgent(
#         name="video_agent",
#         model_client=OpenAIChatCompletionClient(
#             model="gpt-4o-2024-08-06",
#             # api_key="YOUR_API_KEY",
#         ),
#         tools=[get_video_length, get_screenshot_at, save_screenshot, openai_transcribe_video_screenshot, extract_audio, transcribe_audio_with_timestamps],
#         system_message="""
# You are a helpful agent that is an expert at answering questions from videos.

# When asked to answer a question about a video, you should:
# 1. Use the transcription to find which part of the video the question is referring to.
# 2. Optionally use screenshots from those timestamps
# 3. Provide a detailed answer to the question.
# Reply with TERMINATE when the task has been completed.
# """
#     )

#     # Define termination condition
#     termination = TextMentionTermination("TERMINATE")

#     # Define a team
#     agent_team = RoundRobinGroupChat([video_agent], termination_condition=termination)

#     # Run the team and stream messages to the console
#     stream = agent_team.run_stream(task="How does Adam define complex tasks in video.mp4? What concrete example of complex does his use? Can you save this example to disk as well?")
#     await Console(stream)

# asyncio.run(main())
