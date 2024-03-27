import copy
import functools
from typing import Any, Callable, Dict, List, Optional, Union
import warnings

from termcolor import colored

from autogen.agentchat.contrib.capabilities.agent_capability import AgentCapability
from autogen.agentchat.conversable_agent import ConversableAgent
from autogen.cache import Cache
from autogen.agentchat import utils

from .audio_generators import AudioGenerator, GeneratorConfig
from .audio_transcribers import AudioTranscriber, TranscriberConfig

STT_SYSTEM_MESSAGE = """You have the ability to transcribe audio messages.
Here's how to send audio for transcription: <audio file_path='PATH_TO_YOUR_AUDIO_FILE.mp3' task='transcribe'>
REQUIRED ATTRIBUTES:
    - file_path (string): The absolute or relative path to your audio file in a supported format (e.g., mp3, opus).
    - task (string): Set to `transcribe` to indicate you want the audio transcribed.

EXAMPLE:
    <audio file_path='PATH_TO_YOUR_AUDIO_FILE.mp3' task='transcribe'>
    The tag is audio, the file path is PATH_TO_YOUR_AUDIO_FILE.mp3, and the task is transcribe.

EXAMPLE WITH EXTRA ATTRIBUTES:
    <audio file_path='PATH_TO_YOUR_AUDIO_FILE.mp3' task='transcribe' prompt='english accent'>
    This example has an extra attribute: prompt='english accent'.

The user can specify any attributes they like. However, to transcribe audio, they need to specify the file_path and
task set to `transcribe`.

NOTES:
- I'll let you know if you encounter any issues with the audio file or processing.
"""

TTS_SYSTEM_MESSAGE = """You have the the ability to generate audio messages.
Here's how to send audio for generation: <audio text_file='PATH_TO_YOUR_TEXT.txt' task='generate'>
Instead of a text_file, you can also directly specify the text: <audio text='Hello World!' task='generate'>
REQUIRED ATTRIBUTES:
    - Either the text_file or text: The text to generate audio from. If not provided, the audio will be generated from the file path.
    - task (string): Set to `generate` to indicate you want the audio generated.

EXAMPLE:
    <audio text_file='PATH_TO_YOUR_TEXT.txt' task='generate'>
    The tag is audio, the text_file is PATH_TO_YOUR_TEXT.txt, and the task is generate.

EXAMPLE WITH EXTRA ATTRIBUTES:
    <audio text='Hello World!' task='generate' voice='echo'>
    This example has an extra attribute: voice='echo'.

The user can specify any attributes they like. However, to generate audio, they need to specify the text_file or
task, and task set to `generate`.

NOTES:
- I'll let you know if you encounter any issues with the audio file or processing.
"""

STT_SUCCESS_MESSAGE = """
You have received an audio message. {tag}
<AUDIO>
    {transcription}
</AUDIO>
"""

STT_FAILURE_MESSAGE = "NOTE: You have received an audio message. However, you failed to transcribe audio message."

TTS_SUCCESS_MESSAGE = """
You were requested to synthesize an audio message, and you succeeded.
The audio file path is {output_file_path}.
"""

TTS_FAILURE_MESSAGE = "NOTE: You have received a request to synthesize an audio message. However, you failed to do so."


class SpeechToText(AgentCapability):
    """Agent capability to transcribe audio messages into text.

    This capability allows the agent to process audio inputs from users by transcribing the audio into text. The audio
    messages are expected to be sent in the following format:

    <audio file_path='PATH_TO_YOUR_AUDIO_FILE.mp3' task='transcribe'>

    1. Other agent can send audio messages in the above format, where the `file_path` attribute
       points to the local path of the audio file, and the `task` attribute is set to 'transcribe'.

    2. This capability scans the incoming messages from the agent for these audio tags.

    3. Once an audio tag is identified, the capability utilizes the provided AudioTranscriber
       component to transcribe the audio file into text.

    4. The transcribed text is then incorporated into the agent's message processing pipeline,
       replacing the original audio tag.

    ```python
    from autogen.agentchat.capabilities import SpeechToText
    from autogen.agentchat.conversable_agent import ConversableAgent
    from autogen.agentchat.contrib.audio_transcribers import Whisper

    agent = ConversableAgent()
    stt = SpeechToText(audio_transcriber=Whisper())

    stt.add_to_agent(agent)
    ```
    """

    def __init__(self, audio_transcriber: AudioTranscriber, cache: Optional[Cache] = None):
        """
        Args:
            audio_transcriber (AudioTranscriber): The component responsible for transcribing audio data into text.
                This component must implement the AudioTranscriber protocol.
            cache (Cache, optional): An optional cache component to store and retrieve transcriptions.
        """
        self._audio_transcriber = audio_transcriber
        self._cache = cache

    def add_to_agent(self, agent: ConversableAgent):
        """Applies SpeechToText capability to the given agent.

        The following operations will be performed on the agent:
            1. Register a hook on the `process_last_received_message` to transcribe audio messages.
            2. Update the agent's system message with the TTS_SYSTEM_MESSAGE, which indicates to the agent that it can
                transcribe audio.

        Args:
            agent(ConversableAgent): The agent to add the capability to.
        """
        partial_transcribe = functools.partial(_process_audio, hook_func=self._transcribe_audio)
        agent.register_hook(hookable_method="process_last_received_message", hook=partial_transcribe)

        agent.update_system_message(agent.system_message + "\n" + STT_SYSTEM_MESSAGE)

    def _transcribe_audio(self, message: Union[List[Dict], str]) -> Union[List[Dict], str]:
        assert self._audio_transcriber

        tags = utils.parse_tags_from_content("audio", message)
        if not tags:
            return message

        for tag in tags:
            # print(colored(f"Found audio tag: {tag}", "green"))
            transcriber_cfg = tag.get("attr", {})
            if not transcriber_cfg:
                _empty_tag_warn(tag)
                continue

            task = transcriber_cfg.get("task", "")
            if task != "transcribe":
                continue

            # If valid transcriber config, it should be able to build it
            validated_cfg = self._audio_transcriber.build_config(transcriber_cfg)
            if validated_cfg is None:
                warnings.warn(f"Invalid transcriber config: {transcriber_cfg}")
                continue

            transcription = self._transcription_get(validated_cfg)
            if transcription:
                self._transcription_set(validated_cfg, transcription)
                message = _replace_tag_in_message(
                    message, tag, STT_SUCCESS_MESSAGE.format(transcription=transcription, tag=tag["match"].group())
                )
            else:
                warnings.warn(f"Failed to transcribe audio: {transcriber_cfg}")
                message = _replace_tag_in_message(message, tag, STT_FAILURE_MESSAGE)
        # print(colored(f"Processed audio messages: {message}", "green"))

        return message

    def _transcription_get(self, transcriber_cfg: TranscriberConfig) -> Optional[str]:
        assert self._audio_transcriber

        if self._cache:
            key = self._audio_transcriber.cache_key(transcriber_cfg)
            cached = self._cache.get(key)
            if cached:
                return cached

        return self._audio_transcriber.transcribe_audio(transcriber_cfg)

    def _transcription_set(self, transcriber_cfg: TranscriberConfig, transcription: str):
        assert self._audio_transcriber

        if self._cache:
            key = self._audio_transcriber.cache_key(transcriber_cfg)
            self._cache.set(key, transcription)


class TextToSpeech(AgentCapability):
    """Agent capability to generate audio from text messages.

    This capability allows the agent to produce audio outputs by synthesizing text into speech. The audio messages are
    expected to be sent in the following format:

    <audio text='Hello, how are you?' task='generate'>

    1. The agent can send text messages in the above format, where the `text` attribute contains the text to be
       synthesized into audio, and the `task` attribute is set to 'generate'.

    2. This capability scans the incoming messages from the agent for these audio tags.

    3. Once an audio tag is identified, the capability utilizes the provided AudioGenerator component to synthesize the
       text into audio.

    4. The generated audio is saved to a file, and the agent's message is updated with a success message containing the
       output file path.

    ```python
    from autogen.agentchat.capabilities import TextToSpeech
    from autogen.agentchat.conversable_agent import ConversableAgent
    from autogen.agentchat.contrib.audio_generators import Coqui

    agent = ConversableAgent()
    tts = TextToSpeech(audio_generator=Coqui())

    tts.add_to_agent(agent)
    ```
    """

    def __init__(self, audio_generator: AudioGenerator, cache: Optional[Cache] = None):
        """
        Args:
            audio_generator (AudioGenerator): The component responsible for synthesizing text into audio.
                This component must implement the AudioGenerator protocol.
            cache (Cache, optional): An optional cache component to store and retrieve generated audio.
        """
        self._audio_generator = audio_generator
        self._cache = cache

    def add_to_agent(self, agent: ConversableAgent):
        """Applies TextToSpeech capability to the given agent.

        The following operations will be performed on the agent:
            1. Register a hook on the `process_last_received_message` to generate audio messages.
            2. Update the agent's system message with the TTS_SYSTEM_MESSAGE, which indicates to the agent that it can
                generate audio.

        Args:
            agent (ConversableAgent): The agent to add the capability to.
        """
        partial_generate = functools.partial(_process_audio, hook_func=self._generate_audio)
        agent.register_hook(hookable_method="process_last_received_message", hook=partial_generate)

    def _generate_audio(self, message: Union[List[Dict], str]) -> Union[List[Dict], str]:
        assert self._audio_generator

        tags = utils.parse_tags_from_content("audio", message)
        if not tags:
            return message

        for tag in tags:
            generator_cfg = tag.get("attr", {})
            if not generator_cfg:
                _empty_tag_warn(tag)
                continue

            task = generator_cfg.get("task", "")
            if task != "generate":
                continue

            # If valid generator config, it should be able to build it
            validated_cfg = self._audio_generator.build_config(generator_cfg)
            if validated_cfg is None:
                warnings.warn(f"Invalid generator config: {generator_cfg}")
                continue

            audio = self._audio_get(validated_cfg)
            if audio:
                message = _replace_tag_in_message(
                    message, tag, TTS_SUCCESS_MESSAGE.format(output_file_path=validated_cfg.output_file_path)
                )
            else:
                warnings.warn(f"Failed to generate audio: {generator_cfg}")
                message = _replace_tag_in_message(message, tag, TTS_FAILURE_MESSAGE)

        return message

    def _audio_get(self, generator_cfg: GeneratorConfig) -> Optional[bytes]:
        assert self._audio_generator

        if self._cache:
            key = self._audio_generator.cache_key(generator_cfg)
            cached = self._cache.get(key)
            if cached:
                return cached

        audio = self._audio_generator.generate_audio(generator_cfg)
        if audio is not None:
            with open(generator_cfg.output_file_path, "wb") as f:
                f.write(audio)
            return audio

        else:
            return None

    def _audio_set(self, generator_cfg: GeneratorConfig, audio: Optional[bytes]):
        assert self._audio_generator

        if self._cache:
            key = self._audio_generator.cache_key(generator_cfg)
            self._cache.set(key, audio)


def _replace_tag_in_message(
    message: Union[List[Dict], str], tag: Dict[str, Any], replacement_text: str
) -> Union[List[Dict], str]:
    message = copy.deepcopy(message)
    if isinstance(message, List):
        return _multimodal_replace_tag_in_message(message, tag, replacement_text)
    else:
        return message.replace(tag["match"].group(), replacement_text)


def _multimodal_replace_tag_in_message(message: List[Dict], tag: Dict[str, Any], replacement_text: str) -> List[Dict]:
    for m in message:
        if m.get("type") == "text":
            m["text"] = m["text"].replace(tag["match"].group(), replacement_text)
    return message


def _process_audio(message: Union[List[Dict], str], hook_func: Callable):
    if isinstance(message, str):
        return hook_func(message)
    elif isinstance(message, list):
        return [hook_func(m) for m in message]
    else:
        print(colored(f"Unsupported message type: {type(message)}", "yellow"))
        return message


def _empty_tag_warn(tag: Dict):
    print(warnings.warn(f"Found an empty {tag['tag']} tag in message without any content."))
