import threading
import time
import queue

import os
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav


def print_numbers(stop_event, result_queue):
    i = 1
    result = []
    while not stop_event.is_set():
        result.append(i)
        print(
            i,
        )
        i += 1
        time.sleep(1)
    result_queue.put(result)


import requests
from bs4 import BeautifulSoup
import time


def stream_words_from_wiki(stop_event, result_queue):
    url = "https://en.wikipedia.org/wiki/Barack_Obama"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text()
    words = text.split()

    result = []
    for word in words:
        if stop_event.is_set():
            break
        print(
            word,
        )
        result.append(word)
        time.sleep(1)  # sleep for a bit between words for the "streaming" effect
    result_queue.put(result)


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

    print(f"Recording saved to {filename}")
    result_queue.put(filename)


def start_printing_numbers_while_input_received(callable_func=print_numbers):
    stop_thread = threading.Event()
    result_queue = queue.Queue()
    thread = threading.Thread(target=callable_func, args=(stop_thread, result_queue))
    started = False

    print("Press enter to start/stop.")

    while True:
        input()

        if started:
            if thread.is_alive():
                stop_thread.set()
                thread.join()
                stop_thread.clear()
                print("Thread stopped. You can't start it again.")
                result = result_queue.get()
                print("Result: ", result)
                break
        else:
            started = True
            print("Starting thread.")
            thread.start()


if __name__ == "__main__":
    # start_printing_numbers_while_input_received(callable_func=print_numbers)
    # start_printing_numbers_while_input_received(callable_func=stream_words_from_wiki)
    start_printing_numbers_while_input_received(callable_func=record_audio)
