# alternative api: https://rapidapi.com/omarmhaimdat/api/youtube-v2


def get_youtube_caption(videoId):
    """
    Retrieves the captions for a YouTube video.

    Args:
        videoId (str): The ID of the YouTube video.

    Returns:
        str: The captions of the YouTube video in text format.

    Raises:
        KeyError: If the RAPID_API_KEY environment variable is not set.
    """
    import os

    import requests

    RAPID_API_KEY = os.environ["RAPID_API_KEY"]
    url = "https://youtube-captions-and-transcripts.p.rapidapi.com/getCaptions"

    querystring = {"videoId": videoId, "lang": "en", "format": "text"}

    headers = {"X-RapidAPI-Key": RAPID_API_KEY, "X-RapidAPI-Host": "youtube-captions-and-transcripts.p.rapidapi.com"}

    response = requests.get(url, headers=headers, params=querystring)
    response = response.json()
    return response["data"]
