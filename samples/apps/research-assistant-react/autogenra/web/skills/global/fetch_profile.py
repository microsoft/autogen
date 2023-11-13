from typing import Optional
import requests
from bs4 import BeautifulSoup


def fetch_user_profile(url: str) -> Optional[str]:
    """
    Fetches the text content from a personal website.

    Given a URL of a person's personal website, this function scrapes
    the content of the page and returns the text found within the <body>.

    Args:
        url (str): The URL of the person's personal website.

    Returns:
        Optional[str]: The text content of the website's body, or None if any error occurs.
    """
    try:
        # Send a GET request to the URL
        response = requests.get(url)
        # Check for successful access to the webpage
        if response.status_code == 200:
            # Parse the HTML content of the page using BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            # Extract the content of the <body> tag
            body_content = soup.find("body")
            # Return all the text in the body tag, stripping leading/trailing whitespaces
            return " ".join(body_content.stripped_strings) if body_content else None
        else:
            # Return None if the status code isn't 200 (success)
            return None
    except requests.RequestException:
        # Return None if any request-related exception is caught
        return None
