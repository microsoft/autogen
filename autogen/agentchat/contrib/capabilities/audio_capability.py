import copy
import functools
from typing import Any, Callable, Dict, List, Optional, Union
import warnings


import autogen
from autogen.agentchat.contrib.capabilities.agent_capability import AgentCapability
from autogen.agentchat.conversable_agent import ConversableAgent
from autogen.cache import Cache
from autogen.agentchat import utils

from .audio_generators import AudioGenerator, GeneratorConfig
from .audio_transcribers import AudioTranscriber, TranscriberConfig

AUDIO_INTERACTION = """
If you see this tag <AUDIO_INTERACTION_SUCCESS> that means you have successfully processed an audio interaction with the message
    being the transcribed audio.
If you see this tag <AUDIO_INTERACTION_ERROR> that means you have encountered an error while processing an audio
    interaction with the message being the error you faced.
"""

TAG_EXPLANATION = """
The <audio> tag is a specialized tag used to communicate through audio with other agents or users. It allows you to send
and receive audio files for transcription or generate audio from text. The tag accepts various attributes to specify
the desired operation and additional parameters.

EXAMPLE:
    <audio file_path='PATH_TO_YOUR_AUDIO_FILE.mp3' task='transcribe'>
    The tag is audio, the file path is PATH_TO_YOUR_AUDIO_FILE.mp3, and the task is transcribe.

EXAMPLE WITH EXTRA ATTRIBUTES:
    <audio file_path='PATH_TO_YOUR_AUDIO_FILE.mp3' task='transcribe' prompt='english accent'>
    This example has an extra attribute: prompt='english accent'.
"""

STT_SYSTEM_MESSAGE = """You have the ability to transcribe audio messages.

REQUIRED AUDIO ATTRIBUTES:
    {required_attributes}

OPTIONAL AUDIO ATTRIBUTES:
    {optional_attributes}

EXAMPLE:
    <audio file_path='PATH_TO_YOUR_AUDIO_FILE.mp3' task='transcribe'>
    The tag is audio, the file path is PATH_TO_YOUR_AUDIO_FILE.mp3, and the task is transcribe as attributes.

The user can specify any attributes they like. However, to transcribe audio, they need to specify the file_path and
task set to `transcribe`.

NOTES:
- I'll let you know if you encounter any issues with the audio file or processing.
"""

TTS_SYSTEM_MESSAGE = """You have the the ability to generate/synthesize audio messages (Text to Speech).

REQUIRED AUDIO ATTRIBUTES:
    {required_attributes}
OPTIONAL AUDIO ATTRIBUTES:
    {optional_attributes}

EXAMPLE:
    <audio text_file='PATH_TO_YOUR_TEXT.txt' task='generate'>
    The tag is audio, the text_file is PATH_TO_YOUR_TEXT.txt, and the task is generate.

EXAMPLE WITH TEXT:
    <audio text='Hello World!' task='generate'>
    The tag is audio, the text is 'Hello World!', and the task is generate.

EXAMPLE WITH EXTRA ATTRIBUTES:
    <audio text='Hello World!' task='generate' voice='echo'>
    This example has an extra attribute: voice='echo'.

You can specify any attribute they like. However, to generate audio, they need to specify the text_file or
text and task set to `generate` as attributes.

NOTES:
- If tasked to generate/synthesize audio, or you think you need to generate an audio, ALWAYS respond with the appropriate generate audio tag with the correct attributes.

Example:
    'Sure, this is an audio message with the text Hello World! <audio text='Hello World!' task='generate'>'

    `Yes I can use a different voice <audio text='Hello World!' task='generate' voice='echo'>`
"""

STT_RESPONSE_TEMPLATES = {
    "success": """NOTE: You received a request to transcribe and audio message `{tag}`,
        <AUDIO_INTERACTION_SUCCESS>
            {transcription}
        </AUDIO_INTERACTION_SUCCESS>
        """,
    "error": """NOTE: You received a request to transcribe and audio message `{tag}`,
        <AUDIO_INTERACTION_ERROR>
            Unfortunately, you encountered an error during the audio interaction process. {error}.
        </AUDIO_INTERACTION_ERROR>
        """,
}

TTS_RESPONSE_TEMPLATES = {
    "success": """NOTE: An audio message was generated with '{tag}'.
        <AUDIO_INTERACTION_SUCCESS>
            The audio generated and saved in {output_file_path}.
        </AUDIO_INTERACTION_SUCCESS>""",
    "error": """NOTE: You have received a request to synthesize an audio message `{tag}`.
        <AUDIO_INTERACTION_ERROR>
            Unfortunately, I have encountered an error during the audio interaction process. {error}.
        </AUDIO_INTERACTION_ERROR>
        """,
}


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
            2. Update the agent's system message:
                - It explains how the taggins system works.
                - It indicates that the agent has the capability to transcribe audio messages.

        Args:
            agent(ConversableAgent): The agent to add the capability to.
        """
        partial_transcribe = functools.partial(_process_audio, hook_func=self._transcribe_audio)
        agent.register_hook(hookable_method="process_last_received_message", hook=partial_transcribe)

        agent.update_system_message(agent.system_message + "\n" + AUDIO_INTERACTION)
        agent.update_system_message(agent.system_message + "\n" + TAG_EXPLANATION)
        agent.update_system_message(
            agent.system_message
            + "\n"
            + STT_SYSTEM_MESSAGE.format(
                required_attributes=self._audio_transcriber.config.required_attributes_message(),
                optional_attributes=self._audio_transcriber.config.optional_attributes_message(),
            )
        )

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
            try:
                validated_cfg = self._audio_transcriber.build_config(transcriber_cfg)
            except Exception as e:
                warnings.warn(f"Invalid transcriber config: {transcriber_cfg}")
                message = _replace_tag_in_message(
                    message, tag, STT_RESPONSE_TEMPLATES["error"].format(tag=tag["attr"], error=str(e))
                )
                continue

            try:
                transcription = self._transcription_get(validated_cfg)
            except Exception as e:
                warnings.warn(f"Failed to transcribe audio: {transcriber_cfg}")
                message = _replace_tag_in_message(
                    message, tag, STT_RESPONSE_TEMPLATES["error"].format(tag=tag["attr"], error=str(e))
                )
                continue

            self._transcription_set(validated_cfg, transcription)
            message = _replace_tag_in_message(
                message,
                tag,
                STT_RESPONSE_TEMPLATES["success"].format(tag=tag["attr"], transcription=transcription),
            )

        return message

    def _transcription_get(self, transcriber_cfg: TranscriberConfig) -> str:
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
            2. Update the agent's system message:
                - It explains how the tagging system works.
                - It indicates that the agent has the capability to convert text to speech.
        Args:
            agent (ConversableAgent): The agent to add the capability to.
        """
        agent.register_hook(hookable_method="process_message_before_send", hook=self._generate_audio_hook)

        agent.update_system_message(agent.system_message + "\n" + AUDIO_INTERACTION)
        agent.update_system_message(agent.system_message + "\n" + TAG_EXPLANATION)
        agent.update_system_message(
            agent.system_message
            + "\n"
            + TTS_SYSTEM_MESSAGE.format(
                required_attributes=self._audio_generator.config.required_attributes_message(),
                optional_attributes=self._audio_generator.config.optional_attributes_message(),
            )
        )

    def _generate_audio_hook(
        self, sender: autogen.Agent, message: Union[Dict, str], recipient: autogen.Agent, silent: bool
    ) -> Union[Dict, str]:
        if isinstance(message, str):
            content = self._generate_audio(sender, message, recipient, silent)
            if isinstance(content, str):
                return content
            else:
                return {"content": content}
        elif isinstance(message, dict) and "content" in message:
            content = self._generate_audio(sender, message["content"], recipient, silent)
            message["content"] = content
            return message
        else:
            return message

    def _generate_audio(
        self, sender: autogen.Agent, message: Union[List[Dict], str], recipient: autogen.Agent, silent: bool
    ) -> Union[List[Dict], str]:
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
            try:
                validated_cfg = self._audio_generator.build_config(generator_cfg)
            except Exception as e:
                warnings.warn(f"Invalid generator config: {generator_cfg}")
                message = _replace_tag_in_message(
                    message, tag, TTS_RESPONSE_TEMPLATES["error"].format(tag=tag["attr"], error=str(e))
                )
                continue

            try:
                self._audio_get(validated_cfg)
            except Exception as e:
                warnings.warn(f"Failed to generate audio: {generator_cfg}")
                message = _replace_tag_in_message(
                    message, tag, TTS_RESPONSE_TEMPLATES["error"].format(tag=tag["attr"], error=str(e))
                )
                continue

            message = _replace_tag_in_message(
                message,
                tag,
                TTS_RESPONSE_TEMPLATES["success"].format(
                    tag=tag["attr"], output_file_path=validated_cfg.output_file_path
                ),
            )

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
        warnings.warn(f"Unsupported message type: {type(message)}")
        return message


def _empty_tag_warn(tag: Dict):
    warnings.warn(f"Found an empty {tag['tag']} tag in message without any content.")
