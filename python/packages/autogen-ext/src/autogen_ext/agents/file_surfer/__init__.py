try:
    from ._file_surfer import FileSurfer
except ImportError as e:
    raise ImportError(
        f"Dependencies for FileSurfer agent not found: {e}\n"
        'Please install autogen-ext with the "file-surfer" extra: '
        'pip install "autogen-ext[file-surfer]"'
    ) from e

__all__ = ["FileSurfer"]
