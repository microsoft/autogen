try:
    from ._multimodal_web_surfer import MultimodalWebSurfer
    from .playwright_controller import PlaywrightController
except ImportError as e:
    raise ImportError(
        f"Dependencies for MultimodalWebSurfer agent not found: {e}\n"
        'Please install autogen-ext with the "web-surfer" extra: '
        'pip install "autogen-ext[web-surfer]"'
    ) from e

__all__ = ["MultimodalWebSurfer", "PlaywrightController"]
