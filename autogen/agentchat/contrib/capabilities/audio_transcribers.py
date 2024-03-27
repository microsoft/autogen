import os
from typing import Dict, List, Literal, Optional, Protocol

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


MODEL_CONFIG = ConfigDict(extra="allow", populate_by_name=True, validate_assignment=True)


class TranscriberConfig(BaseModel):
    """Configuration model for audio transcribers."""

    file_path: Optional[str] = Field(default=None, description="The path of the audio you want to transcribe.")

    model_config = MODEL_CONFIG

    @classmethod
    def required_attributes_message(cls) -> str:
        return """
        - file_path (string): The absolute or relative path to your audio file in a supported format (e.g., mp3, opus).
        """

    @classmethod
    def optional_attributes_message(cls) -> str:
        return ""

    @model_validator(mode="before")
    def set_file_path(cls, values):
        values["file_path"] = values.get("file_path") or values.get("src")
        return values

    @field_validator("file_path")
    def validate_file_path(cls, value):
        if value:
            if not os.path.isfile(value):
                raise ValueError(f"File not found: {value}")
        return value


class AudioTranscriber(Protocol):
    """Interface definition for audio transcribers."""

    def build_config(self, config: Dict) -> TranscriberConfig:
        """Builds and validates a TranscriberConfig instance from the provided configuration dictionary.

        Returns the validated TranscriberConfig or None if the configuration is invalid.
        """
        ...

    def transcribe_audio(self, transcriber_config: TranscriberConfig) -> str:
        """Transcribes the audio file specified in the given TranscriberConfig instance.

        Returns the transcribed text or None if the transcription fails.
        """
        ...

    def cache_key(self, transcriber_config: TranscriberConfig) -> str:
        """Generates a cache key for the given TranscriberConfig instance.

        This key should be unique for each combination of configuration settings.
        """
        ...

    @property
    def config(self) -> TranscriberConfig: ...


# Implementations of transcribers


class WhisperConfig(TranscriberConfig):
    """Configuration model for OpenAI's Whisper audio transcriber."""

    model: Literal["whisper-1"] = Field(default="whisper-1", description="ID of the model to use.")
    language: str = Field(default="en", description="The language of the input audio. Must ISO-639-1 format.")
    prompt: Optional[str] = Field(
        default=None,
        description=(
            "An optional text to guide the model's style or continue a previous audio segment."
            "The prompt should match the audio language."
        ),
    )
    response_format: Literal["json", "text", "srt", "verbose_json", "vtt"] = Field(
        default="json", description="The format of the transcript output."
    )
    temperature: float = Field(
        default=0.0,
        description=(
            "The sampling temperature, between 0 and 1. Higher values like 0.8 will make the output more random,"
            "while lower values like 0.2 will make it more focused and deterministic."
        ),
    )
    timestamp_granularities: Optional[List[str]] = Field(
        default=None, description="The timestamp granularities to populate for this transcription."
    )

    @classmethod
    def required_attributes_message(cls) -> str:
        return super().required_attributes_message()

    @classmethod
    def optional_attributes_message(cls) -> str:
        return (
            super().optional_attributes_message()
            + """
        - model (Literal["whisper-1"]): ID of the model to use. Only Whisper-1 is currently available.
        - language (string): The language of the input audio. Must ISO-639-1 format.
        - prompt (string): An optional text to guide the model's style or continue a previous audio segment.
            The prompt should match the audio language.
        - response_format (Literal["json", "text", "srt", "verbose_json", "vtt"]): The format of the transcript output.
        - temperature (float): The sampling temperature, between 0 and 1. Higher values like 0.8 will make the output
          more random, while lower values like 0.2 will make it more focused and deterministic.
          Values must be between 0 and 1.
        - timestamp_granularities (List[Literal["word", "segment"]]): The timestamp granularities to populate for this transcription. The response_format must be `verbose_json`.
        """
        )

    @field_validator("response_format")
    def validate_response_format(cls, value):
        if value not in ["json", "text", "srt", "verbose_json", "vtt"]:
            raise ValueError("Response format must be 'json', 'text', 'srt', 'verbose_json' or 'vtt'.")
        return value

    @field_validator("temperature")
    def validate_temperature(cls, value):
        if not 0 <= value <= 1:
            raise ValueError("Temperature must be between 0 and 1.")
        return value

    @field_validator("timestamp_granularities")
    def validate_timestamp_granularities(cls, value):
        if value is not None and cls.response_format != "verbose_json":
            raise ValueError("The response format must be 'verbose_json' to use timestamp granularities.")

        if value is not None and not all(x in ["word", "segment"] for x in value):
            raise ValueError("Timestamp granularities must be 'word' or 'sentence'.")
        return value


class Whisper:
    """Audio transcriber that uses OpenAI's speech-to-text API."""

    def __init__(self, llm_config: Dict, default_whisper_config: WhisperConfig = WhisperConfig()):
        self._default_whisper_config = default_whisper_config
        config_list = llm_config["config_list"]

        self._oai_client = OpenAI(api_key=config_list[0]["api_key"])

    def build_config(self, config: Dict) -> TranscriberConfig:
        built_config = self._default_whisper_config.model_copy(update=config)
        # Ensures validators are called
        return WhisperConfig(**built_config.model_dump())

    def transcribe_audio(self, transcriber_config: TranscriberConfig) -> str:
        assert transcriber_config.file_path, "File path is required"

        audio = open(transcriber_config.file_path, "rb")
        transcription = self._oai_client.audio.transcriptions.create(
            model=transcriber_config.model,
            file=audio,
            response_format=transcriber_config.response_format,
            prompt=transcriber_config.prompt,
            temperature=transcriber_config.temperature,
            language=transcriber_config.language,
            timestamp_granularities=transcriber_config.timestamp_granularities,
        )
        return transcription.text

    def cache_key(self, transcriber_config: TranscriberConfig) -> str:
        return (
            f"{transcriber_config.model}_{transcriber_config.language}"
            f"_{transcriber_config.response_format}"
            f"_{transcriber_config.temperature}"
            f"_{transcriber_config.timestamp_granularities}"
            f"_{transcriber_config.file_path}"
        )

    @property
    def config(self) -> TranscriberConfig:
        return self._default_whisper_config
