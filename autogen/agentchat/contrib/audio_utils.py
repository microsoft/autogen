from typing import Optional
from urllib import request
from urllib import parse

from termcolor import colored


def download_audio_from_url(url: str) -> Optional[bytes]:
    """Downloads an audio file from a URL and returns its content as bytes."""
    try:
        return request.urlopen(url)
    except Exception as e:
        print(colored(f"Error downloading audio from {url}: {e}", "yellow"))
        return None


def download_audio_from_file(file_path: str) -> Optional[bytes]:
    """Downloads an audio file from a file path and returns its content as bytes."""
    try:
        with open(file_path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        print(colored(f"File not found: {file_path}", "yellow"))
        return None
    except Exception as e:
        print(colored(f"Error reading audio file: {e}", "yellow"))
        return None


def download_audio(url_or_file_path: str) -> Optional[bytes]:
    """Downloads an audio file from a URL or file path and returns its content as bytes."""
    parsed_url = parse.urlparse(url_or_file_path)
    if parsed_url.scheme in ["http", "https"]:
        return download_audio_from_url(url_or_file_path)
    else:
        return download_audio_from_file(url_or_file_path)
