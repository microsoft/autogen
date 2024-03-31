from typing import Dict, Protocol
from openai import OpenAI

import speech_recognition as sr


class AudioTranscriber(Protocol):
    def transcribe(self, audio_file_path: str, params: Dict = dict()) -> str: ...


class GoogleTranscriber:
    def __init__(
        self,
        default_params: Dict = {
            "credentials_json": None,
            "language": "en-US",
            "preferred_phrases": None,
            "show_all": False,
        },
    ) -> None:
        self._default_params = default_params
        self._recognizer = sr.Recognizer()

    def transcribe(self, audio_file_path: str, params: Dict = dict()) -> str:
        transcriber_params = {**self._default_params, **params}
        with sr.AudioFile(audio_file_path) as source:
            audio = self._recognizer.record(source)
            return self._recognizer.recognize_google_cloud(audio, **transcriber_params).strip()


class WhisperTranscriber:
    def __init__(
        self,
        default_params: Dict = {
            "api_key": "",
            "model": "whisper-1",
            "language": "en",
            "prompt": None,
            "temperature": 0.0,
        },
    ) -> None:
        if not default_params.get("api_key"):
            raise ValueError("OpenAI API key is required.")

        self._default_params = default_params
        self._oai_client = OpenAI(api_key=default_params["api_key"])

    def transcribe(self, audio_file_path: str, params: Dict = dict()) -> str:
        transcriber_params = {**self._default_params, **params}
        audio = open(audio_file_path, "rb")

        transcription = self._oai_client.audio.transcriptions.create(
            file=audio,
            model=transcriber_params["model"],
            response_format="json",
            prompt=transcriber_params["prompt"],
            temperature=transcriber_params["temperature"],
            language=transcriber_params["language"],
        )
        return transcription.text
