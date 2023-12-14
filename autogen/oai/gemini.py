"""Create a OpenAI-compatible client for Gemini features.

Resources:
- https://ai.google.dev/docs
- https://cloud.google.com/vertex-ai/docs/generative-ai/migrate-from-azure
- https://blog.google/technology/ai/google-gemini-pro-imagen-duet-ai-update/
- https://ai.google.dev/api/python/google/generativeai/ChatSession
"""

from __future__ import annotations

import os
import pdb
import random
import time
from typing import Any, Dict, List, Mapping, Union

import google.generativeai as genai
import httpx
from google.ai.generativelanguage import Content, Part
from google.generativeai import ChatSession
from openai import OpenAI, _exceptions, resources
from openai._qs import Querystring
from openai._types import NOT_GIVEN, NotGiven, Omit, ProxiesTypes, RequestOptions, Timeout, Transport
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion import ChatCompletionMessage, Choice
from openai.types.completion_usage import CompletionUsage
from proto.marshal.collections.repeated import RepeatedComposite
from pydash import max_
from typing_extensions import Self, override

from autogen.token_count_utils import count_token


class GeminiClient:
    """
    _summary_

    _extended_summary_

    TODO: this Gemini implementation does not support the following features yet:
    - function_call (OpenAI)
    - tool_calls (OpenAI)
    - safety_setting (Gemini)
    - Multi-turn chat for vision model (Gemini)
    - multiple responses at the same time (Gemini)
    """

    def __init__(self, **kwargs):
        self.api_key = kwargs.get("api_key", None)
        if self.api_key is None:
            self.api_key = os.getenv("GOOGLE_API_KEY")

        assert self.api_key is not None, (
            "Please provide api_key in OAI_CONFIG_LIST " "or set the GOOGLE_API_KEY env variable."
        )

    def call(self, params: Dict) -> ChatCompletion:
        model_name = params.get("model", "gemini-pro")
        params.get("api_type", "google")  # not used
        messages = params.get("messages", [])
        stream = params.get("stream", False)
        n_response = params.get("n", 1)
        params.get("temperature", 0.5)
        params.get("top_p", 1.0)
        params.get("max_tokens", 1024)
        # TODO: handle these parameters in GenerationConfig

        if stream:
            # TODO: support streaming
            # warn user that streaming is not supported
            print("Streaming is not supported for Gemini yet. Please set stream=False.")

        if n_response > 1:
            print("Gemini only supports `n=1` for now. We only generate one response.")

        # 1. Convert input
        gemini_messages = oai_messages_to_gemini_messages(messages)

        # 2. call gemini client
        if model_name == "gemini-pro":
            # we use chat model by default
            model = genai.GenerativeModel(model_name)
            genai.configure(api_key=self.api_key)
            chat = model.start_chat(history=gemini_messages[:-1])

            response = chat.send_message(gemini_messages[-1].parts[0].text, stream=stream)

            # ans = response.text # failed. Not sure why.
            ans: str = chat.history[-1].parts[0].text
        elif model_name == "gemini-pro-vision":
            # Gemini's vision model does not support chat history yet
            model = genai.GenerativeModel(model_name)
            genai.configure(api_key=self.api_key)
            # chat = model.start_chat(history=gemini_messages[:-1])
            # response = chat.send_message(gemini_messages[-1])
            history: List = [msg["parts"] for msg in gemini_messages]
            history = sum(history)  # 2D list into 1D list
            response = model.generate_content(history)
            ans = response.text

        # 3. convert output
        message = ChatCompletionMessage(role="assistant", content=ans, function_call=None, tool_calls=None)
        choices = [Choice(finish_reason="stop", index=0, message=message)]
        # choices = [Choice(finish_reason="stop", index=0,  text=ans)]

        prompt_tokens = count_token(params["messages"], model_name)
        completion_tokens = count_token(ans, model_name)

        response_oai = ChatCompletion(
            id=random.randint(0, 1000),
            model=model_name,
            created=time.time(),
            object="chat.completion",
            choices=choices,
            usage=CompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
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
                rst.append(Part(image=Part.Image(url=msg["image_url"]["url"])))
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

    concatenated_parts.append(previous_part)

    # TODO: handle inline_data, function_call, function_response

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

    assert rst[-1].role == "user", "The last message must be from the user role."

    # from termcolor import colored
    # print(colored(f"Converted messages: {rst}", "green"))

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
