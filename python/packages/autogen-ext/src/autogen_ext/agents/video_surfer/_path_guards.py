"""Shared path checks for VideoSurfer tools.

extract_audio already refused URLs and writes outside the working
directory. save_screenshot did not. Keep the rules in one place.
"""

from __future__ import annotations

import os
import re

_URL_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+\-.]*://")


def reject_url_path(path: str, *, field_name: str) -> None:
    """Reject a path that looks like a URL (SSRF via ffmpeg/OpenCV)."""
    if _URL_SCHEME.match(path):
        raise ValueError(f"{field_name} must be a local file path, not a URL.")


def ensure_output_within_cwd(output_path: str, *, field_name: str) -> None:
    """Reject an output path that resolves outside the current working directory."""
    cwd = os.path.realpath(os.getcwd())
    output_real = os.path.realpath(output_path)
    if not output_real.startswith(cwd + os.sep) and output_real != cwd:
        raise ValueError(f"{field_name} must be within the current working directory.")
