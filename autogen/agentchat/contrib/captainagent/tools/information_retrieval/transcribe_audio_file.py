from autogen.coding.func_with_reqs import with_requirements


@with_requirements(["openai-whisper"])
def transcribe_audio_file(file_path):
    """
    Transcribes the audio file located at the given file path.

    Args:
        file_path (str): The path to the audio file.

    Returns:
        str: The transcribed text from the audio file.
    """
    import whisper

    model = whisper.load_model("base")
    result = model.transcribe(file_path)
    return result["text"]
