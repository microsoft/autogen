"""VideoSurfer extract_audio already refused URLs and writes outside cwd.

save_screenshot did not. These tests mock the video-surfer extra so they
run without opencv/ffmpeg/whisper.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

for _name in ("cv2", "ffmpeg", "whisper"):
    sys.modules.setdefault(_name, MagicMock())

try:
    import numpy  # noqa: F401
except ImportError:
    sys.modules.setdefault("numpy", MagicMock())

from autogen_ext.agents.video_surfer.tools import extract_audio, save_screenshot


def test_extract_audio_rejects_url_video_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="local file path"):
        extract_audio("https://example.com/video.mp4", "out.mp3")


def test_extract_audio_rejects_output_outside_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="current working directory"):
        extract_audio("video.mp4", "../escaped.mp3")


def test_save_screenshot_rejects_url_video_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="local file path"):
        save_screenshot("https://example.com/video.mp4", 0.0, "frame.png")


def test_save_screenshot_rejects_output_outside_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="current working directory"):
        save_screenshot("video.mp4", 0.0, "../escaped.png")


def test_save_screenshot_rejects_absolute_output_outside_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    outside = tmp_path.parent / "escaped.png"
    with pytest.raises(ValueError, match="current working directory"):
        save_screenshot("video.mp4", 0.0, str(outside))
