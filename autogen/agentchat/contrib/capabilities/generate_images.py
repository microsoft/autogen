import abc
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
from diskcache import Cache
import re

from openai import OpenAI
from autogen.agentchat.agent import Agent
from autogen.agentchat.contrib import img_utils
from .agent_capability import AgentCapability
from autogen.agentchat.contrib.text_analyzer_agent import TextAnalyzerAgent

from PIL.Image import Image
from autogen import ConversableAgent

SYSTEM_MESSAGE = "You've been given the special ability to generate images."
DESCRIPTION_MESSAGE = "This agent has the ability to generate images."


class ImageGenerator(abc.ABC):
    @abc.abstractmethod
    def generate_image(self, prompt: str) -> Image:
        raise NotImplementedError()


class DalleImageGenerator(ImageGenerator):
    def __init__(
        self,
        llm_config: Dict,
        resolution: Literal["256x256", "512x512", "1024x1024", "1792x1024", "1024x1792"] = "1024x1024",
        quality: Literal["standard", "hd"] = "standard",
        num_images: int = 1,
    ):
        config_list = llm_config["config_list"]
        _validate_dalle_model(config_list[0]["model"])
        _validate_resolution_format(resolution)

        self._model = config_list[0]["model"]
        self._resolution = resolution
        self._quality = quality
        self._num_images = num_images
        self._dalle_client = OpenAI(api_key=config_list[0]["api_key"])

    def generate_image(self, prompt: str) -> Image:
        """Got this from Beibin Li's work in agentchat_dalle_and_gpt4v.ipynb"""
        # Function implementation...
        cache = Cache(".cache/")  # Create a cache directory
        key = (self._model, prompt, self._resolution, self._quality, self._num_images)

        if key in cache:
            return img_utils._to_pil(cache[key])

        # If not in cache, compute and store the result
        response = self._dalle_client.images.generate(
            model=self._model,
            prompt=prompt,
            size=self._resolution,
            quality=self._quality,
            n=self._num_images,
        )
        image_url = response.data[0].url
        img_data = img_utils.get_image_data(image_url)
        cache[key] = img_data
        return img_utils._to_pil(img_data)


class ImageGeneration(AgentCapability):
    def __init__(
        self, image_generator: ImageGenerator, text_analyzer_llm_config: Optional[Dict] = None, verbosity: int = 0
    ):
        self._image_generator = image_generator
        self._text_analyzer_llm_config = text_analyzer_llm_config
        self._verbosity = verbosity

        self._agent: Optional[ConversableAgent] = None
        self._text_analyzer: Optional[TextAnalyzerAgent] = None

    def add_to_agent(self, agent: ConversableAgent):
        self._agent = agent

        agent.register_reply([Agent, None], self._image_gen_reply, position=2)

        self._text_analyzer_llm_config = self._text_analyzer_llm_config or agent.llm_config
        self._text_analyzer = TextAnalyzerAgent(llm_config=self._text_analyzer_llm_config)

        agent.update_system_message(agent.system_message + "\n" + SYSTEM_MESSAGE)
        # Hack to update the description of the agent, useful when used in a group chat
        agent.description += "\n" + DESCRIPTION_MESSAGE

    def _image_gen_reply(
        self,
        reciepient: ConversableAgent,
        messages: Optional[List[Dict]],
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        if messages is None:
            return False, None

        last_message = messages[-1]["content"]
        if isinstance(last_message, dict):
            last_message = last_message.get("text", "")

        if not last_message:
            return False, None

        if self._should_generate_image(last_message):
            prompt = self._analyze_text(
                last_message,
                "In detail, please provide the prompt to generate the image described in the TEXT. DO NOT include any advice.",
            )
            image = self._image_generator.generate_image(prompt)

            # TODO: DELETE THIS AFTER TESTING
            image.show()

            return True, {
                "content": [
                    {"type": "text", "text": f"Generated an image with the prompt: {prompt}"},
                    {"type": "image_url", "image_url": {"url": image}},
                ]
            }
        else:
            return False, None

    def _should_generate_image(self, message: str) -> bool:
        response = self._analyze_text(
            message,
            "Does any part of the TEXT ask the agent to generate or modify an image? Answer with just one word, yes or no.",
        )
        return "yes" in response.lower()

    def _analyze_text(self, text_to_analyze: str, analysis_instructions: str) -> str:
        assert self._text_analyzer is not None
        assert self._agent is not None

        self._text_analyzer.reset()
        self._agent.send(
            recipient=self._text_analyzer, message=text_to_analyze, request_reply=False, silent=self._verbosity < 2
        )
        self._agent.send(
            recipient=self._text_analyzer, message=analysis_instructions, request_reply=True, silent=self._verbosity < 2
        )

        return self._agent.last_message(self._text_analyzer)["content"]


### Helpers
def _validate_resolution_format(resolution: str):
    """Checks if a string is in a valid resolution format (e.g., "1024x768")."""
    pattern = r"^\d+x\d+$"  # Matches a pattern of digits, "x", and digits
    return bool(re.match(pattern, resolution))


def _validate_dalle_model(model: str):
    if model not in ["dall-e-3", "dall-e-2"]:
        raise ValueError(f"Invalid DALL-E model: {model}. Must be 'dall-e-3' or 'dall-e-2'")
