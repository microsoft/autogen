import os
import tempfile

import pytest
from conftest import MOCK_OPEN_AI_API_KEY, skip_openai

from autogen.agentchat.contrib.capabilities.audio_generators import TTS
from autogen.agentchat.contrib.capabilities.audio_transcribers import Whisper
from autogen.oai import openai_utils

test_dir = os.path.join(os.path.dirname(__file__), "../../..", "test_files")


def api_key():
    return MOCK_OPEN_AI_API_KEY if skip_openai else os.environ.get("OPENAI_API_KEY")


def llm_config(model: str):
    config_list = openai_utils.config_list_from_models(model_list=[model], exclude="aoai")
    if not config_list:
        config_list = [{"model": model, "api_key": api_key()}]

    return {"config_list": config_list, "timeout": 120, "cache_seed": None}


@pytest.mark.skipif(skip_openai, reason="Requested to skip openai tests.")
def test_whisper_transcriber():
    transcriber = Whisper(llm_config=llm_config("whisper-1"))

    new_config = {"task": "transcribe", "language": "en", "file_path": os.path.join(test_dir, "hello_autogen.mp3")}
    whisper_config = transcriber.build_config(new_config)

    assert whisper_config

    transcribed_text = transcriber.transcribe_audio(whisper_config)

    assert isinstance(transcribed_text, str)
    assert "hello" in transcribed_text.lower()
    assert "autogen" in transcribed_text.lower()


@pytest.mark.skipif(skip_openai, reason="Requested to skip openai tests.")
def test_tts_generator():
    with tempfile.TemporaryDirectory() as temp_dir:
        generator = TTS(llm_config=llm_config("tts-1"))

        new_config = {
            "task": "generate",
            "text": "Hello AutoGen!",
            "output_file_path": os.path.join(temp_dir, "hello_autogen.mp3"),
        }
        tts_config = generator.build_config(new_config)

        assert tts_config

        generated_text = generator.generate_audio(tts_config)

        assert isinstance(generated_text, bytes)

        with open(tts_config.output_file_path, "wb") as f:
            f.write(generated_text)
