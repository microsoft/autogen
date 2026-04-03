try:
    from ._video_surfer import VideoSurfer
except ImportError as e:
    raise ImportError(
        f"Dependencies for VideoSurfer agent not found: {e}\n"
        'Please install autogen-ext with the "video-surfer" extra: '
        'pip install "autogen-ext[video-surfer]"'
    ) from e

__all__ = ["VideoSurfer"]
