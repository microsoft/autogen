import os
import autogen
from autogen.agentchat.contrib.capabilities.audio_capability import SpeechToText, TextToSpeech
from autogen.agentchat.contrib.capabilities.audio_generators import TTS, TTSConfig
from autogen.agentchat.contrib.capabilities.audio_transcribers import Whisper, WhisperConfig
from autogen.agentchat.conversable_agent import ConversableAgent
from autogen.agentchat.user_proxy_agent import UserProxyAgent


if __name__ == "__main__":
    gpt_llm_config = {
        "config_list": [
            {
                "model": "gpt-4-0125-preview",
                "api_key": os.environ["OPENAI_API_KEY"],
            }
        ]
    }
    whisper_llm_config = {
        "config_list": [
            {
                "model": "whisper-1",
                "api_key": os.environ["OPENAI_API_KEY"],
            }
        ]
    }
    tts_llm_config = {
        "config_list": [
            {
                "model": "tts-1",
                "api_key": os.environ["OPENAI_API_KEY"],
            }
        ]
    }

    agent = ConversableAgent(name="agent", llm_config=gpt_llm_config)
    user_agent = UserProxyAgent(name="user")

    stt = SpeechToText(audio_transcriber=Whisper(whisper_llm_config))

    tts = TextToSpeech(audio_generator=TTS(llm_config=tts_llm_config))

    stt.add_to_agent(agent)
    tts.add_to_agent(agent)

    # user_agent.initiate_chat(
    #     recipient=agent,
    #     max_turns=4,
    #     message="What does this audio message say? <audio file_path='test/test_files/hello_autogen.mp3' task='transcribe'>",
    # )

    msg = "Can you count to 5 and tell me what's being said in this audio message? <audio file_path='test/test_files/hello_autogen.mp3' task='transcribe'>"
    msg = input("Enter message: ")

    user_agent.initiate_chat(
        recipient=agent,
        message=msg,
    )
