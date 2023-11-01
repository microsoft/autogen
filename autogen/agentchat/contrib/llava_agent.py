import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union

import replicate
import requests
from regex import R

from autogen.agentchat.agent import Agent
from autogen.agentchat.multimodal_conversable_agent import MultimodalConversableAgent
from autogen.img_utils import get_image_data, lmm_formater

try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x


logger = logging.getLogger(__name__)

# we will override the following variables later.
MODEL_NAME = ""
SEP = "###"

DEFAULT_LLAVA_SYS_MSG = "You are an AI agent and you can view images."


class LLaVAAgent(MultimodalConversableAgent):
    def __init__(
        self,
        name: str,
        system_message: Optional[Tuple[str, List]] = DEFAULT_LLAVA_SYS_MSG,
        *args,
        **kwargs,
    ):
        """
        Args:
            name (str): agent name.
            system_message (str): system message for the ChatCompletion inference.
                Please override this attribute if you want to reprogram the agent.
            **kwargs (dict): Please refer to other kwargs in
                [ConversableAgent](conversable_agent#__init__).
        """
        super().__init__(
            name,
            system_message=system_message,
            *args,
            **kwargs,
        )

        assert self.llm_config is not None, "llm_config must be provided."
        self.register_reply([Agent, None], reply_func=LLaVAAgent._image_reply, position=0)

    def _image_reply(self, messages=None, sender=None, config=None):
        # Note: we did not use "llm_config" yet.
        # TODO 1: make the LLaVA API design compatible with llm_config

        if all((messages is None, sender is None)):
            error_msg = f"Either {messages=} or {sender=} must be provided."
            logger.error(error_msg)
            raise AssertionError(error_msg)

        if messages is None:
            messages = self._oai_messages[sender]

        # The formats for LLaVA and GPT are different. So, we manually handle them here.
        # TODO: format the images from the history accordingly.
        images = []
        prompt = self._content_str(self.system_message) + "\n"
        for msg in messages:
            role = "Human" if msg["role"] == "user" else "Assistant"
            images += [d["image"] for d in msg["content"] if isinstance(d, dict)]
            content_prompt = self._content_str(msg["content"])
            prompt += f"{SEP}{role}: {content_prompt}\n"
        prompt += "\n" + SEP + "Assistant: "
        print(colored(prompt, "blue"))

        out = ""
        retry = 10
        while len(out) == 0 and retry > 0:
            # image names will be inferred automatically from llava_call
            out = llava_call_binary(
                prompt=prompt,
                images=images,
                config_list=self.llm_config["config_list"],
                temperature=self.llm_config.get("temperature", 0.5),
                max_new_tokens=self.llm_config.get("max_new_tokens", 2000),
            )
            retry -= 1

        assert out != "", "Empty response from LLaVA."

        return True, out


def _llava_call_binary_with_config(
    prompt: str, images: list, config: dict, max_new_tokens: int = 1000, temperature: float = 0.5, seed: int = 1
):
    if config["api_base"].find("0.0.0.0") >= 0 or config["api_base"].find("localhost") >= 0:
        llava_mode = "local"
    else:
        llava_mode = "remote"

    if llava_mode == "local":
        headers = {"User-Agent": "LLaVA Client"}
        pload = {
            "model": config["model"],
            "prompt": prompt,
            "max_new_tokens": max_new_tokens,
            "temperature": temperature,
            "stop": SEP,
            "images": images,
        }

        response = requests.post(
            os.path.join(config["api_base"], "worker_generate_stream"), headers=headers, json=pload, stream=False
        )

        for chunk in response.iter_lines(chunk_size=8192, decode_unicode=False, delimiter=b"\0"):
            if chunk:
                data = json.loads(chunk.decode("utf-8"))
                output = data["text"].split(SEP)[-1]
    elif llava_mode == "remote":
        # The Replicate version of the model only support 1 image for now.
        img = "data:image/jpeg;base64," + images[0]
        response = replicate.run(
            config["api_base"], input={"image": img, "prompt": prompt.replace("<image>", " "), "seed": seed}
        )
        # The yorickvp/llava-13b model can stream output as it's running.
        # The predict method returns an iterator, and you can iterate over that output.
        output = ""
        for item in response:
            # https://replicate.com/yorickvp/llava-13b/versions/2facb4a474a0462c15041b78b1ad70952ea46b5ec6ad29583c0b29dbd4249591/api#output-schema
            output += item

    # Remove the prompt and the space.
    output = output.replace(prompt, "").strip().rstrip()
    return output


def llava_call_binary(
    prompt: str, images: list, config_list: list, max_new_tokens: int = 1000, temperature: float = 0.5, seed: int = 1
):
    # TODO 1: add caching around the LLaVA call to save compute and cost
    # TODO 2: add `seed` to ensure reproducibility. The seed is not working now.

    for config in config_list:
        try:
            return _llava_call_binary_with_config(prompt, images, config, max_new_tokens, temperature, seed)
        except Exception as e:
            print(f"Error: {e}")
            continue


def llava_call(
    prompt: str,
    model_name: str = MODEL_NAME,
    images: list = [],
    max_new_tokens: int = 1000,
    temperature: float = 0.5,
    seed: int = 1,
) -> str:
    """
    Makes a call to the LLaVA service to generate text based on a given prompt and optionally provided images.

    Args:
        - prompt (str): The input text for the model. Any image paths or placeholders in the text should be replaced with "<image>".
        - model_name (str, optional): The name of the model to use for the text generation. Defaults to the global constant MODEL_NAME.
        - images (list, optional): A list of image paths or URLs. If not provided, they will be extracted from the prompt.
            If provided, they will be appended to the prompt with the "<image>" placeholder.
        - max_new_tokens (int, optional): Maximum number of new tokens to generate. Defaults to 1000.
        - temperature (float, optional): temperature for the model. Defaults to 0.5.

    Returns:
        - str: Generated text from the model.

    Raises:
        - AssertionError: If the number of "<image>" tokens in the prompt and the number of provided images do not match.
        - RunTimeError: If any of the provided images is empty.

    Notes:
    - Any image paths or URLs in the prompt are automatically replaced with the "<image>" token.
    - If more images are provided than there are "<image>" tokens in the prompt, the extra tokens are appended to the end of the prompt.
    """

    if len(images) == 0:
        prompt, images = lmm_formater(prompt, order_image_tokens=False)
    else:
        # Append the <image> token if missing
        assert prompt.count("<image>") <= len(images), "the number "
        "of image token in prompt and in the images list should be the same!"
        num_token_missing = len(images) - prompt.count("<image>")
        prompt += " <image> " * num_token_missing
        images = [get_image_data(x) for x in images]

    for im in images:
        if len(im) == 0:
            raise RuntimeError("An image is empty!")

    return llava_call_binary(prompt, images, model_name, max_new_tokens, temperature, seed)
