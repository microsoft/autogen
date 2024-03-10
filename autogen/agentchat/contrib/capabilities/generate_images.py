import re
from typing import Any, Dict, List, Literal, Optional, Protocol, Tuple, Union

from openai import OpenAI
from PIL.Image import Image

from autogen import Agent, ConversableAgent, code_utils
from autogen.cache import Cache
from autogen.agentchat.contrib import img_utils
from autogen.agentchat.contrib.capabilities.agent_capability import AgentCapability
from autogen.agentchat.contrib.text_analyzer_agent import TextAnalyzerAgent

SYSTEM_MESSAGE = "You've been given the special ability to generate images."
DESCRIPTION_MESSAGE = "This agent has the ability to generate images."


class ImageGenerator(Protocol):
    """This class defines an interface for image generators.

    Concrete implementations of this protocol must provide a `generate_image` method that takes a string prompt as
    input and returns a PIL Image object.
    """

    def generate_image(self, prompt: str) -> Image:
        """Generates an image based on the provided prompt.

        Args:
          prompt: A string describing the desired image.

        Returns:
          A PIL Image object representing the generated image.

        Raises:
          ValueError: If the image generation fails.
        """
        ...

    def cache_key(self, prompt: str) -> str:
        """Generates a unique cache key for the given prompt.

        This key can be used to store and retrieve generated images based on the prompt.

        Args:
          prompt: A string describing the desired image.

        Returns:
          A unique string that can be used as a cache key.
        """
        ...


class DalleImageGenerator:
    def __init__(
        self,
        llm_config: Dict,
        resolution: Literal["256x256", "512x512", "1024x1024", "1792x1024", "1024x1792"] = "1024x1024",
        quality: Literal["standard", "hd"] = "standard",
        num_images: int = 1,
    ):
        """
        Args:
            llm_config (dict): llm config, must contain a valid dalle model and OpenAI API key in config_list.
            resolution (str): The resolution of the image you want to generate. Must be one of "256x256", "512x512", "1024x1024", "1792x1024", "1024x1792".
            quality (str): The quality of the image you want to generate. Must be one of "standard", "hd".
            num_images (int): The number of images to generate.
        """
        config_list = llm_config["config_list"]
        _validate_dalle_model(config_list[0]["model"])
        _validate_resolution_format(resolution)

        self._model = config_list[0]["model"]
        self._resolution = resolution
        self._quality = quality
        self._num_images = num_images
        self._dalle_client = OpenAI(api_key=config_list[0]["api_key"])

    def generate_image(self, prompt: str) -> Image:
        response = self._dalle_client.images.generate(
            model=self._model,
            prompt=prompt,
            size=self._resolution,
            quality=self._quality,
            n=self._num_images,
        )

        image_url = response.data[0].url
        if image_url is None:
            raise ValueError("Failed to generate image.")

        return img_utils.get_pil_image(image_url)

    def cache_key(self, prompt: str) -> str:
        keys = (prompt, self._model, self._resolution, self._quality, self._num_images)
        return ",".join([str(k) for k in keys])


class ImageGeneration(AgentCapability):
    def __init__(
        self,
        image_generator: ImageGenerator,
        cache: Optional[Cache] = None,
        text_analyzer_llm_config: Optional[Dict] = None,
        verbosity: int = 0,
    ):
        """
        Args:
            image_generator (ImageGenerator): The image generator you would like to use to generate images.
            text_analyzer_llm_config (Dict or None): The LLM config for the text analyzer. Defaults to None.
            verbosity (int): The verbosity level. Defaults to 0 and must be greater than or equal to 0. The text
            analyzer llm calls will be silent if verbosity is less than 2.
        """
        self._image_generator = image_generator
        self._cache = cache
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
        recipient: ConversableAgent,
        messages: Optional[List[Dict]],
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        if messages is None:
            return False, None

        last_message = code_utils.content_str(messages[-1]["content"])

        if not last_message:
            return False, None

        if self._should_generate_image(last_message):
            assert self._text_analyzer is not None

            instructions = """In detail, please summarize the provided prompt to generate the image described in the
            TEXT. DO NOT include any advice. RESPOND like the following example:
            EXAMPLE: Blue background, 3D shapes, ...
            """
            analysis = self._text_analyzer.analyze_text(last_message, instructions)
            prompt = self._extract_analysis(analysis)

            image = self._cache_get(prompt)
            if image is None:
                image = self._image_generator.generate_image(prompt)
                self._cache_set(prompt, image)

            return True, self._generate_content_message(prompt, image)

        else:
            return False, None

    def _should_generate_image(self, message: str) -> bool:
        assert self._text_analyzer is not None

        instructions = """
        Does any part of the TEXT ask the agent to generate an image?
        The TEXT must explicitly mention that the image must be generated.
        Answer with just one word, yes or no.
        """
        analysis = self._text_analyzer.analyze_text(message, instructions)

        return "yes" in self._extract_analysis(analysis).lower()

    def _cache_get(self, prompt: str) -> Optional[Image]:
        if self._cache:
            key = self._image_generator.cache_key(prompt)
            cached_value = self._cache.get(key)

            if cached_value:
                return img_utils.get_pil_image(cached_value)

    def _cache_set(self, prompt: str, image: Image):
        if self._cache:
            key = self._image_generator.cache_key(prompt)
            self._cache.set(key, img_utils.pil_to_data_uri(image))

    def _extract_analysis(self, analysis: Union[str, Dict, None]) -> str:
        if isinstance(analysis, Dict):
            return code_utils.content_str(analysis["content"])
        else:
            return code_utils.content_str(analysis)

    def _generate_content_message(self, prompt: str, image: Image) -> Dict[str, Any]:
        return {
            "content": [
                {"type": "text", "text": f"I generated an image with the prompt: {prompt}"},
                {"type": "image_url", "image_url": {"url": img_utils.pil_to_data_uri(image)}},
            ]
        }


### Helpers
def _validate_resolution_format(resolution: str):
    """Checks if a string is in a valid resolution format (e.g., "1024x768")."""
    pattern = r"^\d+x\d+$"  # Matches a pattern of digits, "x", and digits
    matched_resolution = re.match(pattern, resolution)
    if matched_resolution is None:
        raise ValueError(f"Invalid resolution format: {resolution}")


def _validate_dalle_model(model: str):
    if model not in ["dall-e-3", "dall-e-2"]:
        raise ValueError(f"Invalid DALL-E model: {model}. Must be 'dall-e-3' or 'dall-e-2'")
