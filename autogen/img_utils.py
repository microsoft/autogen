import base64
import mimetypes
import re
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from PIL import Image


def get_image_data(image_file: str, use_b64=True) -> bytes:
    if image_file.startswith("http://") or image_file.startswith("https://"):
        response = requests.get(image_file)
        content = response.content
    elif re.match(r"data:image/(?:png|jpeg);base64,", image_file):
        return re.sub(r"data:image/(?:png|jpeg);base64,", "", image_file)
    else:
        image = Image.open(image_file).convert("RGB")
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        content = buffered.getvalue()

    if use_b64:
        return base64.b64encode(content).decode("utf-8")
    else:
        return content


def llava_formater(prompt: str, order_image_tokens: bool = False) -> Tuple[str, List[str]]:
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


def gpt4v_formatter(prompt: str) -> List[Union[str, dict]]:
    """
    Formats the input prompt by replacing image tags and returns a list of text and images.

    Parameters:
        - prompt (str): The input string that may contain image tags like <img ...>.

    Returns:
        - List[Union[str, dict]]: A list of alternating text and image dictionary items.
    """
    output = []
    last_index = 0
    image_count = 0

    # Regular expression pattern for matching <img ...> tags
    img_tag_pattern = re.compile(r"<img ([^>]+)>")

    # Find all image tags
    for match in img_tag_pattern.finditer(prompt):
        image_location = match.group(1)

        try:
            img_data = get_image_data(image_location)
        except Exception as e:
            # Warning and skip this token
            print(f"Warning! Unable to load image from {image_location}, because {e}")
            continue

        # Add text before this image tag to output list
        output.append({"type": "text", "text": prompt[last_index : match.start()]})

        # Add image data to output list
        output.append({"type": "image_url", "image_url": {"url": convert_base64_to_data_uri(img_data)}})

        last_index = match.end()
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
        data (str): The base64 encoded image data string.

    Returns:
        Image.Image: The PIL Image object created from the input data.
    """
    return Image.open(BytesIO(base64.b64decode(data)))
