from typing import Dict, Literal, Optional, Protocol

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MODEL_CONFIG = ConfigDict(extra="allow", populate_by_name=True, validate_assignment=True)


class GeneratorConfig(BaseModel):
    """Configuration model for audio generators."""

    text_file: Optional[str] = Field(
        alias="src",
        default=None,
        description="File path of the text you want to generate audio from. If not provided, the audio will be generated from the text.",
    )
    text: Optional[str] = Field(
        default=None,
        description="Text to generate audio from. If not provided, the audio will be generated from the file path.",
    )

    output_file_path: str = Field(
        default="generated_audio.mp3",
        description="File path to save the generated audio to. If not provided, the audio will not be saved.",
    )

    model_config = MODEL_CONFIG

    @classmethod
    def required_attributes_message(self) -> str:
        return """
        - Either the text_file or text: The text to generate audio from. If not provided, the audio will be generated from the file path.
        """

    @classmethod
    def optional_attributes_message(cls) -> str:
        return """
        output_file_path (str): The file path and name to save the generated audio to.
            Must include the appropriate file extension.
        """

    @classmethod
    def validate_text(cls, value: str):
        if value is not None:
            cls.text = value
        return value

    @model_validator(mode="before")
    def set_file_path(cls, values):
        values["text_file"] = values.get("text_file") or values.get("src")
        return values

    @field_validator("text_file")
    def validate_file_path(cls, value: str):
        if value is not None and cls.text is None:
            cls.text = _read_file(value)
        return value


class AudioGenerator(Protocol):
    """Defines the interface for audio generators."""

    def build_config(self, config: Dict) -> GeneratorConfig:
        """Builds and validates a GeneratorConfig instance from the provided configuration dictionary.

        Returns the validated GeneratorConfig or None if the configuration is invalid.
        """
        ...

    def generate_audio(self, generator_config: GeneratorConfig) -> bytes:
        """Generates audio data based on the provided GeneratorConfig instance.

        Returns the generated audio data as bytes, or None if the generation fails.
        """
        ...

    def cache_key(self, generator_config: GeneratorConfig) -> str:
        """Generates a cache key for the given GeneratorConfig instance.

        This key should be unique for each combination of configuration settings.
        """
        ...

    @property
    def config(self) -> GeneratorConfig: ...


# Implementations of audio generators


class TTSConfig(GeneratorConfig):
    """Configuration implementation for OpenAI's text-to-speech audio generation."""

    model: Literal["tts-1", "tts-1-hd"] = Field(default="tts-1", description="TTS model to use.")
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = Field(
        default="alloy", description="TTS voice to use."
    )
    response_format: Literal["mp3", "opus", "aac", "flac"] = Field(default="mp3", description="Audio format.")
    speed: float = Field(default=1.0, description="Audio speed. Must be between 0.25 and 4.")

    @classmethod
    def required_attributes_message(cls) -> str:
        return super().required_attributes_message()

    @classmethod
    def optional_attributes_message(cls) -> str:
        return """
        - model (Literal["tts-1", "tts-1-hd"]): OpenAI's TTS model to use. Only "tts-1" and "tts-1-hd" are supported.
        - voice (Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"]): TTS voice to use.
            alloy (str): A male voice model with a warm and friendly tone. Suitable for virtual assistants, audiobook
                narration, and educational content.
            echo (str): A female voice model with a clear and expressive tone. Often used for storytelling, voice-over
                work, and podcasts.
            fable (str): A female voice model with a gentle and soothing tone. Well-suited for applications that require
                a calming and reassuring voice, such as meditation apps or bedtime stories.
            onyx (str): A male voice model with a deep and authoritative tone. Useful for applications that require a
                commanding or professional voice, such as corporate presentations or voiceovers for documentaries.
            nova (str): A female voice model with a bright and energetic tone. Good for applications that require a
                lively and engaging voice, such as advertising or promotional videos.
            shimmer (str): A female voice model with a clear and natural tone. Versatile choice for various
                applications, including e-learning content, virtual assistants, and audiobook narration.
        - response_format (str): Audio format. Only "mp3", "opus", "aac", and "flac" are supported.
        - speed (float): Audio speed. Must be between 0.25 and 4.
        """

    @field_validator("speed")
    def validate_speed(cls, value):
        if not 0.25 <= value <= 4.0:
            raise ValueError("Speed must be between 0.25 and 4.")
        return value


class TTS:
    """Generates audio data using OpenAI's text-to-speech API."""

    def __init__(self, llm_config: Dict, default_tts_config: GeneratorConfig = TTSConfig()):
        self._default_tts_config = default_tts_config
        config_list = llm_config["config_list"]

        self._oai_client = OpenAI(api_key=config_list[0]["api_key"])

    def build_config(self, config: Dict) -> TTSConfig:
        built_config = self._default_tts_config.model_copy(update=config)
        # Ensures validators are called
        return TTSConfig(**built_config.model_dump())

    def generate_audio(self, generator_config: GeneratorConfig) -> bytes:
        # Makes sure we either have the text or the text file to synthesize
        if generator_config.text:
            text = generator_config.text
        elif generator_config.text_file:
            text = _read_file(generator_config.text_file)
        else:
            raise ValueError("Text or text file is required")

        response = self._oai_client.audio.speech.create(
            input=text,
            model=generator_config.model,
            voice=generator_config.voice,
            response_format=generator_config.response_format,
            speed=generator_config.speed,
        )

        return response.content

    def cache_key(self, generator_config: GeneratorConfig) -> str:
        return (
            f"{generator_config.model}_{generator_config.voice}"
            f"_{generator_config.speed}_{generator_config.text or generator_config.text_file}"
        )

    @property
    def config(self) -> GeneratorConfig:
        return self._default_tts_config


def _read_file(file_path: str) -> str:
    with open(file_path, "r") as f:
        return f.read()
