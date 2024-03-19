from typing import Any, Callable, Dict, List, Literal, Optional, Protocol, Union
import copy

from termcolor import colored

from autogen.agentchat.contrib.capabilities.agent_capability import AgentCapability
from autogen.agentchat.conversable_agent import ConversableAgent
from autogen.cache import Cache
from autogen.agentchat.contrib import audio_utils


class AudioGenerator(Protocol):
    def generate_audio(self, text: str, generator_config: Optional[Dict] = None) -> bytes:
        ...

    def cache_key(self, text: str, generator_config: Optional[Dict] = None) -> str:
        ...

    def validated_config(self, config: Dict) -> Optional[Dict]:
        ...


class AudioTranscriber(Protocol):
    def transcribe_audio(self, audio_bytes: bytes, transcriber_config: Optional[Dict] = None) -> str:
        ...

    def cache_key(self, transcriber_config: Optional[Dict] = None) -> str:
        ...

    def validated_config(self, config: Dict) -> Optional[Dict]:
        ...


class TTS:
    """OpenAI's text-to-speech API."""

    def __init__(
        self,
        default_model: Literal["tts-1", "tts-1-hd"] = "tts-1",
        default_voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = "alloy",
        default_response_format: Literal["mp3", "opus", "aac", "flac", "wav", "pcm"] = "mp3",
        default_speed: float = 1.0,
    ):
        self._validate_speed(default_speed)

        self._default_model = default_model
        self._default_voice = default_voice
        self._default_response_format = default_response_format
        self._default_speed = default_speed

    def generate_audio(self, text: str, generator_config: Dict = dict()) -> bytes:
        pass

    def cache_key(self, generator_config: Dict = dict()) -> str:
        pass

    def _validate_model(self, model: str):
        if model not in ["tts-1", "tts-1-hd"]:
            raise ValueError("Model must be either 'tts-1' or 'tts-1-hd'.")

    def _validate_voice(self, voice: str):
        if voice not in ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]:
            raise ValueError("Voice must be one of 'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'.")

    def _validate_response_format(self, response_format: str):
        if response_format not in ["mp3", "opus", "aac", "flac", "wav", "pcm"]:
            raise ValueError("Response format must be one of 'mp3', 'opus', 'aac', 'flac', 'wav', 'pcm'.")

    def _validate_speed(self, speed: float):
        if not 0.25 <= speed <= 4.0:
            raise ValueError("Speed must be between 0.25 and 4.")


class Whisper:
    """OpenAI's speech-to-text API."""

    def __init__(
        self,
        default_model: Literal["whisper-1"] = "whisper-1",
        default_language: str = "en",
        default_response_format: Literal["json", "text", "srt", "verbose_json", "vtt"] = "json",
        default_temperature: float = 0.0,
        defualt_timestamp_granularities: Optional[List[str]] = None,
    ):
        self._validate_temperature(default_temperature)
        self._validate_timestamp_granularities(defualt_timestamp_granularities, default_response_format)

        self._default_model = default_model
        self._default_language = default_language
        self._default_response_format = default_response_format
        self._default_temperature = default_temperature
        self._default_timestamp_granularities = defualt_timestamp_granularities

    def transcribe_audio(self, audio_bytes: bytes, transcriber_config: Optional[Dict] = None) -> Optional[str]:
        pass

    def cache_key(self, transcriber_config: Dict) -> Optional[str]:
        validated_cfg = self.validated_config(transcriber_config)

        if validated_cfg is None:
            return None
        else:
            return (
                f"{validated_cfg['file_path']}_{validated_cfg['model']}_"
                f"{validated_cfg['language']}_{validated_cfg['response_format']}_"
                f"{validated_cfg['temperature']}_{validated_cfg['response_format']}"
            )

    def validated_config(self, config: Dict) -> Optional[Dict]:
        validated_config = copy.deepcopy(config)

        try:
            validated_config["model"] = _return_validated_config(
                self._default_model, config.get("model"), self._validate_model
            )
            validated_config["response_format"] = _return_validated_config(
                self._default_response_format, config.get("response_format"), self._validate_response_format
            )
            validated_config["temperature"] = _return_validated_config(
                self._default_temperature, config.get("temperature"), self._validate_temperature
            )
            validated_config["timestamp_granularities"] = _return_validated_config(
                self._default_timestamp_granularities,
                config.get("timestamp_granularities"),
                self._validate_timestamp_granularities,
            )
            validated_config["file_path"] = config.get("file_path") or config.get("src")
            assert validated_config["file_path"], "No file path provided in transcriber config."
        except ValueError as e:
            print(colored(f"Error in transcriber config, received invalid parameters: {e}", "yellow"))
            return None

        return validated_config

    def _validate_model(self, model: str):
        if model != "whisper-1":
            raise ValueError(f"Model must be 'whisper-1'. Received: {model}")

    def _validate_response_format(self, response_format: str):
        if response_format not in ["json", "text", "srt", "verbose_json", "vtt"]:
            raise ValueError(
                f"Response format must be one of 'json', 'text', 'srt', 'verbose_json', 'vtt'. Received: {response_format}"
            )

    def _validate_temperature(self, temperature: float):
        if not 0 <= temperature <= 1:
            raise ValueError(f"Temperature must be between 0 and 1. Received: {temperature}")

    def _validate_timestamp_granularities(self, timestamp_granularities: Optional[List[str]], response_format: str):
        if timestamp_granularities and response_format != "verbose_json":
            raise ValueError("Timestamp granularities can only be used with 'verbose_json' response format.")


class AudioCapability(AgentCapability):
    """
    required content:
    - file_path or src
    """

    def __init__(
        self,
        audio_transcriber: Optional[AudioTranscriber] = None,
        audio_generator: Optional[AudioGenerator] = None,
        cache: Optional[Cache] = None,
    ):
        _validate_init(audio_transcriber, audio_generator)

        self._audio_transcriber = audio_transcriber
        self._audio_generator = audio_generator
        self._cache = cache

    def add_to_agent(self, agent: ConversableAgent):
        if self._audio_transcriber:
            agent.register_hook(hookable_method="process_last_received_message", hook=self._transcribe_audio)
        if self._audio_generator:
            agent.register_hook(hookable_method="process_message_before_send", hook=self._generate_audio)

    def _transcribe_audio(self, message: Union[List[Dict], str]) -> Union[List[Dict], str]:
        assert self._audio_transcriber

        tags = _fake_parse_content("audio", message)
        if not tags:
            return message

        for tag in tags:
            transcriber_cfg = tag.get("content", {})
            if not transcriber_cfg:
                _empty_tag_warn(tag)
                continue

            validated_cfg = self._audio_transcriber.validated_config(transcriber_cfg)
            if validated_cfg is None:
                print(colored("Invalid transcriber config.", "yellow"))
                continue

            file_path = validated_cfg.get("file_path")
            if not file_path:
                print(colored("No file path provided in transcriber config.", "yellow"))
                continue

            cache_key = self._audio_transcriber.cache_key(validated_cfg)
            audio = self._audio_get(cache_key, file_path)
            if audio is None:
                print(colored("Audio not found", "yellow"))
                continue

            transcription = self._audio_transcriber.transcribe_audio(audio, validated_cfg)
            if transcription:
                tag["content"]["transcription"] = transcription

            # download if not in cache
            # transcribe
            # adjust message accordingly

    def _generate_audio(self, message: Dict, recipient: ConversableAgent, silent: bool) -> Dict[str, List]:
        pass

    def _audio_get(self, cache_key: str, file_path: str) -> Optional[bytes]:
        if self._cache:
            return self._cache.get(cache_key)
        else:
            return audio_utils.download_audio(file_path)


def _return_validated_config(default: Any, config: Optional[Any], validation_func: Callable) -> Any:
    if config is not None:
        if default is None:
            validation_func(config)
            return config
        else:
            config_cast = type(default)(config)
            validation_func(config_cast)
            return config_cast
    else:
        return default


def _validate_init(audio_transcriber: Optional[AudioTranscriber], audio_generator: Optional[AudioGenerator]):
    if not any([audio_transcriber, audio_generator]):
        raise ValueError("At least an audio transcriber or an audio generator must be provided.")


def _empty_tag_warn(tag: Dict):
    print(colored(f"Found an empty {tag['tag']} tag in message without any content.", "yellow"))


def _fake_parse_content(tags: str, message: Union[List[Dict], str]) -> List[Dict[str, Dict[str, str]]]:
    return [{}]
