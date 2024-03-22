import os
import threading
import queue

from openai import OpenAI
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav


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

    print(f"[debug] Recording saved to {filename}")

    client = OpenAI()

    audio_file = open(filename, "rb")
    transcription = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
    result_queue.put(transcription.text)


def speech_to_text(callable_func=record_audio):
    stop_thread = threading.Event()
    result_queue = queue.Queue()
    thread = threading.Thread(target=callable_func, args=(stop_thread, result_queue))
    started = False

    print("Press enter to start/stop recording.")

    while True:
        input()

        if started:
            if thread.is_alive():
                stop_thread.set()
                thread.join()
                stop_thread.clear()
                print("[debug] Thread stopped. You can't start it again.")
                result = result_queue.get()
                print("\nThe user said: ", result)
                break
        else:
            started = True
            print("[debug] Starting thread.")
            thread.start()


if __name__ == "__main__":
    speech_to_text()
