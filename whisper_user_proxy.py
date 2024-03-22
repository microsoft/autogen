import os
import threading
import queue

from openai import OpenAI
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
from autogen import AssistantAgent, UserProxyAgent, Agent


def record_audio(stop_event, result_queue):
    """Record audio from the microphone and save it to a file.

    Args:
    stop_event: An event that will stop the recording when set.
    result_queue: A queue to put the result into.
    """
    filename = "output_2.wav"
    # remove the file if it already exists
    try:
        os.remove(filename)
    except FileNotFoundError:
        pass

    fs = 44100  # Sample rate
    duration = 1  # seconds

    # Create a buffer for the recording
    buffer = np.array([])

    # Create a stream for recording
    stream = sd.InputStream(samplerate=fs, channels=1)

    # Open the stream and start recording
    with stream:
        while not stop_event.is_set():
            recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
            sd.wait()  # Wait for the recording to finish

            # Append the recording to the buffer
            buffer = np.append(buffer, recording)

    # Write the entire recording to the file
    with open(filename, "wb") as f:
        wav.write(f, fs, buffer)

    # print(f"[debug] Recording saved to {filename}")

    client = OpenAI()

    audio_file = open(filename, "rb")
    transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
    result_queue.put(transcription.text)


def speech_to_text(callable_func=record_audio):
    stop_thread = threading.Event()
    result_queue = queue.Queue()
    thread = threading.Thread(target=callable_func, args=(stop_thread, result_queue))
    started = False

    transcription = None

    print("Listening... Press Enter to stop recording.")
    thread.start()

    input()

    if thread.is_alive():
        stop_thread.set()
        thread.join()
        stop_thread.clear()
        print("[debug] Stopped recording...")
        transcription = result_queue.get()
        print("[debug] The user said: ", transcription)

    return transcription


class WhisperUserProxyAgent(UserProxyAgent):

    def get_human_input(self, prompt: str) -> str:
        """Get human input.

        Override this method to customize the way to get human input.

        Args:
            prompt (str): prompt for the human input.

        Returns:
            str: human input.
        """
        reply = input(
            f"Provide feedback to sender.\n- Press enter to skip and use auto-reply,\n- type 'exit' to end the conversation,\n- type 'v' to use voice: "
        )
        if reply == "v":
            reply = speech_to_text()

        self._human_input.append(reply)
        return reply


def demo_whisper_user_proxy():
    config_list = [
        {
            "model": "gpt-4",
            "api_key": os.environ["OPENAI_API_KEY"],
        }
    ]
    assistant = AssistantAgent("assistant", llm_config={"config_list": config_list})
    user_proxy = WhisperUserProxyAgent(
        "voice_user_proxy",
        code_execution_config={"work_dir": "coding", "use_docker": False},
        human_input_mode="ALWAYS",
    )

    assistant.initiate_chat(user_proxy, message="What can I help you with today?")


if __name__ == "__main__":
    # speech_to_text()
    demo_whisper_user_proxy()
