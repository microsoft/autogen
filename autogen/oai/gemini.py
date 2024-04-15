"""Create a OpenAI-compatible client for Gemini features.


Example:
    llm_config={
        "config_list": [{
            "api_type": "google",
            "model": "models/gemini-pro",
            "api_key": os.environ.get("GOOGLE_API_KEY")
            }
    ]}

    agent = autogen.AssistantAgent("my_agent", llm_config=llm_config)

Resources:
- https://ai.google.dev/docs
- https://cloud.google.com/vertex-ai/docs/generative-ai/migrate-from-azure
- https://blog.google/technology/ai/google-gemini-pro-imagen-duet-ai-update/
- https://ai.google.dev/api/python/google/generativeai/ChatSession
"""

from __future__ import annotations

import base64
import os
import random
import re
import time
import warnings
from io import BytesIO
from typing import Any, Dict, List, Mapping, Union

import google.generativeai as genai
import requests
from google.ai.generativelanguage import Content, Part
from google.api_core.exceptions import InternalServerError
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion import ChatCompletionMessage, Choice
from openai.types.completion_usage import CompletionUsage
from PIL import Image

# from autogen.agentchat.contrib.img_utils import _to_pil, get_image_data
from autogen.token_count_utils import count_token


class GeminiClient:
    """Client for Google's Gemini API.

    Please visit this [page](https://github.com/microsoft/autogen/issues/2387) for the roadmap of Gemini integration
    of AutoGen.
    """

    def __init__(self, **kwargs):
        self.api_key = kwargs.get("api_key", None)
        if not self.api_key:
            self.api_key = os.getenv("GOOGLE_API_KEY")

        assert (
            self.api_key
        ), "Please provide api_key in your config list entry for Gemini or set the GOOGLE_API_KEY env variable."

    def message_retrieval(self, response) -> List:
        """
        Retrieve and return a list of strings or a list of Choice.Message from the response.

        NOTE: if a list of Choice.Message is returned, it currently needs to contain the fields of OpenAI's ChatCompletion Message object,
        since that is expected for function or tool calling in the rest of the codebase at the moment, unless a custom agent is being used.
        """
        return [choice.message for choice in response.choices]

    def cost(self, response) -> float:
        return 0.0

    @staticmethod
    def get_usage(response) -> Dict:
        """Return usage summary of the response using RESPONSE_USAGE_KEYS."""
        # ...  # pragma: no cover
        return {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "cost": response.cost,
            "model": response.model,
        }

    def create(self, params: Dict) -> ChatCompletion:
        model_name = params.get("model", "gemini-pro")
        if not model_name:
            raise ValueError(
                "Please provide a model name for the Gemini Client. "
                "You can configurate it in the OAI Config List file. "
                "See this [LLM configuration tutorial](https://microsoft.github.io/autogen/docs/topics/llm_configuration/) for more details."
            )

        params.get("api_type", "google")  # not used
        messages = params.get("messages", [])
        stream = params.get("stream", False)
        n_response = params.get("n", 1)
        params.get("temperature", 0.5)
        params.get("top_p", 1.0)
        params.get("max_tokens", 1024)

        if stream:
            # warn user that streaming is not supported
            warnings.warn(
                "Streaming is not supported for Gemini yet, and it will have no effect. Please set stream=False.",
                UserWarning,
            )

        if n_response > 1:
            warnings.warn("Gemini only supports `n=1` for now. We only generate one response.", UserWarning)

        if "vision" not in model_name:
            # A. create and call the chat model.
            gemini_messages = oai_messages_to_gemini_messages(messages)

            # we use chat model by default
            model = genai.GenerativeModel(model_name)
            genai.configure(api_key=self.api_key)
            chat = model.start_chat(history=gemini_messages[:-1])
            try:
                response = chat.send_message(gemini_messages[-1].parts[0].text, stream=stream)
            except InternalServerError as e:
                print(e)
                warnings.warn(
                    "InternalServerError `500` occurs when calling Gemini's chat model. Retry in 5 seconds...",
                    UserWarning,
                )
                time.sleep(5)
                return self.create(params)
            except Exception as e:
                raise RuntimeError(f"Google GenAI exception occurred while calling Gemini API: {e}")
            else:
                # `ans = response.text` is unstable. Use the following code instead.
                ans: str = chat.history[-1].parts[0].text
        elif model_name == "gemini-pro-vision":
            # B. handle the vision model
            # Gemini's vision model does not support chat history yet
            model = genai.GenerativeModel(model_name)
            genai.configure(api_key=self.api_key)
            # chat = model.start_chat(history=gemini_messages[:-1])
            # response = chat.send_message(gemini_messages[-1])
            user_message = oai_content_to_gemini_content(messages[-1]["content"])
            if len(messages) > 2:
                warnings.warn(
                    "Warning: Gemini's vision model does not support chat history yet.",
                    "We only use the last message as the prompt.",
                    UserWarning,
                )

            response = model.generate_content(user_message, stream=stream)
            # ans = response.text
            ans: str = response._result.candidates[0].content.parts[0].text

        # 3. convert output
        message = ChatCompletionMessage(role="assistant", content=ans, function_call=None, tool_calls=None)
        choices = [Choice(finish_reason="stop", index=0, message=message)]

        prompt_tokens = count_token(params["messages"], model_name)
        completion_tokens = count_token(ans, model_name)

        response_oai = ChatCompletion(
            id=str(random.randint(0, 1000)),
            model=model_name,
            created=int(time.time() * 1000),
            object="chat.completion",
            choices=choices,
            usage=CompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            cost=0,
        )

        return response_oai


def oai_content_to_gemini_content(content: Union[str, List]) -> List:
    """Convert content from OAI format to Gemini format"""
    rst = []
    if isinstance(content, str):
        rst.append(Part(text=content))
        return rst

    assert isinstance(content, list)

    for msg in content:
        if isinstance(msg, dict):
            assert "type" in msg, f"Missing 'type' field in message: {msg}"
            if msg["type"] == "text":
                rst.append(Part(text=msg["text"]))
            elif msg["type"] == "image_url":
                b64_img = get_image_data(msg["image_url"]["url"])
                img = _to_pil(b64_img)
                rst.append(img)
            else:
                raise ValueError(f"Unsupported message type: {msg['type']}")
        else:
            raise ValueError(f"Unsupported message type: {type(msg)}")
    return rst


def concat_parts(parts: List[Part]) -> List:
    """Concatenate parts with the same type.
    If two adjacent parts both have the "text" attribute, then it will be joined into one part.
    """
    if not parts:
        return []

    concatenated_parts = []
    previous_part = parts[0]

    for current_part in parts[1:]:
        if previous_part.text != "":
            previous_part.text += current_part.text
        else:
            concatenated_parts.append(previous_part)
            previous_part = current_part

    if previous_part.text == "":
        previous_part.text = "empty"  # Empty content is not allowed.
    concatenated_parts.append(previous_part)

    return concatenated_parts


def oai_messages_to_gemini_messages(messages: list[Dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert messages from OAI format to Gemini format.
    Make sure the "user" role and "model" role are interleaved.
    Also, make sure the last item is from the "user" role.
    """
    prev_role = None
    rst = []
    curr_parts = []
    for i, message in enumerate(messages):
        parts = oai_content_to_gemini_content(message["content"])
        role = "user" if message["role"] in ["user", "system"] else "model"

        if prev_role is None or role == prev_role:
            curr_parts += parts
        elif role != prev_role:
            rst.append(Content(parts=concat_parts(curr_parts), role=prev_role))
            curr_parts = parts
        prev_role = role

    # handle the last message
    rst.append(Content(parts=concat_parts(curr_parts), role=role))

    # The Gemini is restrict on order of roles, such that
    # 1. The messages should be interleaved between user and model.
    # 2. The last message must be from the user role.
    # We add a dummy message "continue" if the last role is not the user.
    if rst[-1].role != "user":
        rst.append(Content(parts=oai_content_to_gemini_content("continue"), role="user"))

    return rst


def count_gemini_tokens(ans: Union[str, Dict, List], model_name: str) -> int:
    # ans is OAI format in oai_messages
    raise NotImplementedError(
        "Gemini's count_tokens function is not implemented yet in Google's genai. Please revisit!"
    )

    if isinstance(ans, str):
        model = genai.GenerativeModel(model_name)
        return model.count_tokens(ans)  # Error occurs here!
    elif isinstance(ans, dict):
        if "content" in ans:
            # Content dict
            return count_gemini_tokens(ans["content"], model_name)
        if "text" in ans:
            # Part dict
            return count_gemini_tokens(ans["text"], model_name)
        else:
            raise ValueError(f"Unsupported message type: {type(ans)}")
    elif isinstance(ans, list):
        return sum([count_gemini_tokens(msg, model_name) for msg in ans])
    else:
        raise ValueError(f"Unsupported message type: {type(ans)}")


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
