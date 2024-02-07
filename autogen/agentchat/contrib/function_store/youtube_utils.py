from youtube_transcript_api import YouTubeTranscriptApi


def get_youtube_transcript(youtube_link: str) -> str:
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
