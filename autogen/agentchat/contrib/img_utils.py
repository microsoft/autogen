import base64
import copy
import os
import re
from io import BytesIO
from typing import Dict, List, Tuple, Union

import requests
from PIL import Image

from autogen.agentchat import utils


def get_pil_image(image_file: Union[str, Image.Image]) -> Image.Image:
    """
    Loads an image from a file and returns a PIL Image object.

    Parameters:
        image_file (str, or Image): The filename, URL, URI, or base64 string of the image file.

    Returns:
        Image.Image: The PIL Image object.
    """
    if isinstance(image_file, Image.Image):
        # Already a PIL Image object
        return image_file

    # Remove quotes if existed
    if image_file.startswith('"') and image_file.endswith('"'):
        image_file = image_file[1:-1]
    if image_file.startswith("'") and image_file.endswith("'"):
        image_file = image_file[1:-1]

    if image_file.startswith("http://") or image_file.startswith("https://"):
        # A URL file
        response = requests.get(image_file)
        content = BytesIO(response.content)
        image = Image.open(content)
    elif re.match(r"data:image/(?:png|jpeg);base64,", image_file):
        # A URI. Remove the prefix and decode the base64 string.
        base64_data = re.sub(r"data:image/(?:png|jpeg);base64,", "", image_file)
        image = _to_pil(base64_data)
    elif os.path.exists(image_file):
        # A local file
        image = Image.open(image_file)
    else:
        # base64 encoded string
        image = _to_pil(image_file)

    return image.convert("RGB")


def get_image_data(image_file: Union[str, Image.Image], use_b64=True) -> bytes:
    """
    Loads an image and returns its data either as raw bytes or in base64-encoded format.

    This function first loads an image from the specified file, URL, or base64 string using
    the `get_pil_image` function. It then saves this image in memory in PNG format and
    retrieves its binary content. Depending on the `use_b64` flag, this binary content is
    either returned directly or as a base64-encoded string.

    Parameters:
        image_file (str, or Image): The path to the image file, a URL to an image, or a base64-encoded
                          string of the image.
        use_b64 (bool): If True, the function returns a base64-encoded string of the image data.
                        If False, it returns the raw byte data of the image. Defaults to True.

    Returns:
        bytes: The image data in raw bytes if `use_b64` is False, or a base64-encoded string
               if `use_b64` is True.
    """
    image = get_pil_image(image_file)

    buffered = BytesIO()
    image.save(buffered, format="PNG")
    content = buffered.getvalue()

    if use_b64:
        return base64.b64encode(content).decode("utf-8")
    else:
        return content


def llava_formatter(prompt: str, order_image_tokens: bool = False) -> Tuple[str, List[str]]:
    """
    Formats the input prompt by replacing image tags and returns the new prompt along with image locations.

    Parameters:
        - prompt (str): The input string that may contain image tags like <img ...>.
        - order_image_tokens (bool, optional): Whether to order the image tokens with numbers.
            It will be useful for GPT-4V. Defaults to False.

    Returns:
        - Tuple[str, List[str]]: A tuple containing the formatted string and a list of images (loaded in b64 format).
    """

    # Initialize variables
    new_prompt = prompt
    image_locations = []
    images = []
    image_count = 0

    # Regular expression pattern for matching <img ...> tags
    img_tag_pattern = re.compile(r"<img ([^>]+)>")

    # Find all image tags
    for match in img_tag_pattern.finditer(prompt):
        image_location = match.group(1)

        try:
            img_data = get_image_data(image_location)
        except Exception as e:
            # Remove the token
            print(f"Warning! Unable to load image from {image_location}, because of {e}")
            new_prompt = new_prompt.replace(match.group(0), "", 1)
            continue

        image_locations.append(image_location)
        images.append(img_data)

        # Increment the image count and replace the tag in the prompt
        new_token = f"<image {image_count}>" if order_image_tokens else "<image>"

        new_prompt = new_prompt.replace(match.group(0), new_token, 1)
        image_count += 1

    return new_prompt, images


def pil_to_data_uri(image: Image.Image) -> str:
    """
    Converts a PIL Image object to a data URI.

    Parameters:
        image (Image.Image): The PIL Image object.

    Returns:
        str: The data URI string.
    """
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    content = buffered.getvalue()
    return convert_base64_to_data_uri(base64.b64encode(content).decode("utf-8"))


def convert_base64_to_data_uri(base64_image):
    def _get_mime_type_from_data_uri(base64_image):
        # Decode the base64 string
        image_data = base64.b64decode(base64_image)
        # Check the first few bytes for known signatures
        if image_data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        elif image_data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        elif image_data.startswith(b"GIF87a") or image_data.startswith(b"GIF89a"):
            return "image/gif"
        elif image_data.startswith(b"RIFF") and image_data[8:12] == b"WEBP":
            return "image/webp"
        return "image/jpeg"  # use jpeg for unknown formats, best guess.

    mime_type = _get_mime_type_from_data_uri(base64_image)
    data_uri = f"data:{mime_type};base64,{base64_image}"
    return data_uri


def gpt4v_formatter(prompt: str, img_format: str = "uri") -> List[Union[str, dict]]:
    """
    Formats the input prompt by replacing image tags and returns a list of text and images.

    Args:
        - prompt (str): The input string that may contain image tags like <img ...>.
        - img_format (str): what image format should be used. One of "uri", "url", "pil".

    Returns:
        - List[Union[str, dict]]: A list of alternating text and image dictionary items.
    """
    assert img_format in ["uri", "url", "pil"]

    output = []
    last_index = 0
    image_count = 0

    # Find all image tags
    for parsed_tag in utils.parse_tags_from_content("img", prompt):
        image_location = parsed_tag["attr"]["src"]
        try:
            if img_format == "pil":
                img_data = get_pil_image(image_location)
            elif img_format == "uri":
                img_data = get_image_data(image_location)
                img_data = convert_base64_to_data_uri(img_data)
            elif img_format == "url":
                img_data = image_location
            else:
                raise ValueError(f"Unknown image format {img_format}")
        except Exception as e:
            # Warning and skip this token
            print(f"Warning! Unable to load image from {image_location}, because {e}")
            continue

        # Add text before this image tag to output list
        output.append({"type": "text", "text": prompt[last_index : parsed_tag["match"].start()]})

        # Add image data to output list
        output.append({"type": "image_url", "image_url": {"url": img_data}})

        last_index = parsed_tag["match"].end()
        image_count += 1

    # Add remaining text to output list
    output.append({"type": "text", "text": prompt[last_index:]})
    return output


def extract_img_paths(paragraph: str) -> list:
    """
    Extract image paths (URLs or local paths) from a text paragraph.

    Parameters:
        paragraph (str): The input text paragraph.

    Returns:
        list: A list of extracted image paths.
    """
    # Regular expression to match image URLs and file paths
    img_path_pattern = re.compile(
        r"\b(?:http[s]?://\S+\.(?:jpg|jpeg|png|gif|bmp)|\S+\.(?:jpg|jpeg|png|gif|bmp))\b", re.IGNORECASE
    )

    # Find all matches in the paragraph
    img_paths = re.findall(img_path_pattern, paragraph)
    return img_paths


def _to_pil(data: str) -> Image.Image:
    """
    Converts a base64 encoded image data string to a PIL Image object.

    This function first decodes the base64 encoded string to bytes, then creates a BytesIO object from the bytes,
    and finally creates and returns a PIL Image object from the BytesIO object.

    Parameters:
        data (str): The encoded image data string.

    Returns:
        Image.Image: The PIL Image object created from the input data.
    """
    return Image.open(BytesIO(base64.b64decode(data)))


def message_formatter_pil_to_b64(messages: List[Dict]) -> List[Dict]:
    """
    Converts the PIL image URLs in the messages to base64 encoded data URIs.

    This function iterates over a list of message dictionaries. For each message,
    if it contains a 'content' key with a list of items, it looks for items
    with an 'image_url' key. The function then converts the PIL image URL
    (pointed to by 'image_url') to a base64 encoded data URI.

    Parameters:
        messages (List[Dict]): A list of message dictionaries. Each dictionary
                               may contain a 'content' key with a list of items,
                               some of which might be image URLs.

    Returns:
        List[Dict]: A new list of message dictionaries with PIL image URLs in the
                    'image_url' key converted to base64 encoded data URIs.

    Example Input:
        [
            {'content': [{'type': 'text', 'text': 'You are a helpful AI assistant.'}], 'role': 'system'},
            {'content': [
                {'type': 'text', 'text': "What's the breed of this dog here? \n"},
                {'type': 'image_url', 'image_url': {'url': a PIL.Image.Image}},
                {'type': 'text', 'text': '.'}],
            'role': 'user'}
        ]

    Example Output:
        [
            {'content': [{'type': 'text', 'text': 'You are a helpful AI assistant.'}], 'role': 'system'},
            {'content': [
                {'type': 'text', 'text': "What's the breed of this dog here? \n"},
                {'type': 'image_url', 'image_url': {'url': a B64 Image}},
                {'type': 'text', 'text': '.'}],
            'role': 'user'}
        ]
    """
    new_messages = []
    for message in messages:
        # Handle the new GPT messages format.
        if isinstance(message, dict) and "content" in message and isinstance(message["content"], list):
            message = copy.deepcopy(message)
            for item in message["content"]:
                if isinstance(item, dict) and "image_url" in item:
                    item["image_url"]["url"] = pil_to_data_uri(item["image_url"]["url"])

        new_messages.append(message)

    return new_messages
