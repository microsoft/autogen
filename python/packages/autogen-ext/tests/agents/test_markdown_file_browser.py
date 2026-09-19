import os
import pytest
from autogen_ext.agents.file_surfer._markdown_file_browser import MarkdownFileBrowser


def test_markdown_file_browser_cross_drive_validation() -> None:
    """Test that validating cross-drive paths on Windows does not crash with ValueError."""
    browser = MarkdownFileBrowser(base_path=os.getcwd())
    
    # Test path on an inaccessible/different Windows drive or invalid path
    different_drive_path = "Z:\\nonexistent_drive_path\\file.txt"
    assert browser._validate_path(different_drive_path) is False


def test_markdown_file_browser_within_base_path(tmp_path: pytest.TempPathFactory) -> None:
    """Test standard valid and invalid paths."""
    base = tmp_path / "base"
    base.mkdir()
    sub = base / "subdir"
    sub.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    browser = MarkdownFileBrowser(base_path=str(base))
    assert browser._validate_path(str(sub)) is True
    assert browser._validate_path(str(outside)) is False
