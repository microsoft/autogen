from .functions_utils import FunctionWithRequirements


@FunctionWithRequirements(python_packages=["youtube_transcript_api==0.6.0"])
def get_youtube_transcript(youtube_link: str) -> str:
    """
    Gets the transcript of a YouTube video.

    Args:
        youtube_link (str): The link to the YouTube video.

    Returns:
        str: The transcript of the YouTube video.
    """
    from youtube_transcript_api import YouTubeTranscriptApi

    # Extract video ID from the YouTube link
    video_id = youtube_link.split("v=")[1]

    try:
        # Get the transcript for the video
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)

        # Combine all parts of the transcript into a single string
        transcript = " ".join([part["text"] for part in transcript_list])

        return transcript
    except Exception as e:
        return str(e)
