def youtube_download(url: str):
    """
    Downloads a YouTube video and returns the download link.

    Args:
        url: The URL of the YouTube video.

    Returns:
        str: The download link for the audio.
    """
    import os

    import requests

    endpoint = "https://youtube-mp3-downloader2.p.rapidapi.com/ytmp3/ytmp3/"

    querystring = {"url": url}

    headers = {
        "X-RapidAPI-Key": os.environ.get("RAPIDAPI_KEY"),
        "X-RapidAPI-Host": "youtube-mp3-downloader2.p.rapidapi.com",
    }

    response = requests.get(endpoint, headers=headers, params=querystring)
    response = response.json()

    if "link" in response:
        return response["link"]
    else:
        print("Error: Unable to retrieve download link.")
        print(response)
        # or you can return an error message
        # return "Error: Unable to retrieve download link."
