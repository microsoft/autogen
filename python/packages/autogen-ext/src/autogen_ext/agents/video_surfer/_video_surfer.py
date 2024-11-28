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
You are a helpful agent that is an expert at answering questions from a video.
    
When asked to answer a question about a video, you should:
1. Check if that video is available locally.
2. Use the transcription to find which part of the video the question is referring to.
3. Optionally use screenshots from those timestamps
4. Provide a detailed answer to the question.
Reply with TERMINATE when the task has been completed.
""",
description="An agent that can answer questions about a local video.",
        )
