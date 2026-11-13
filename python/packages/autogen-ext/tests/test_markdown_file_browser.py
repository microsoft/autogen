from pathlib import Path

from autogen_ext.agents.file_surfer._markdown_file_browser import MarkdownFileBrowser


def test_opening_another_file_clears_find_next(tmp_path: Path) -> None:
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("needle in the first document", encoding="utf-8")
    second.write_text("needle in the second document", encoding="utf-8")
    browser = MarkdownFileBrowser(base_path=str(tmp_path), cwd=str(tmp_path))
    browser.open_path(str(first))
    assert browser.find_on_page("needle") is not None

    browser.open_path(str(second))

    assert browser.find_next() is None


def test_same_query_on_new_file_starts_from_current_viewport(tmp_path: Path) -> None:
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("needle first", encoding="utf-8")
    second.write_text("needle first page " + "padding " * 10 + "needle last page", encoding="utf-8")
    browser = MarkdownFileBrowser(viewport_size=20, base_path=str(tmp_path), cwd=str(tmp_path))
    browser.open_path(str(first))
    assert browser.find_on_page("needle") is not None

    browser.open_path(str(second))

    assert browser.find_on_page("needle") is not None
    assert browser.viewport_current_page == 0


def test_find_next_still_cycles_within_current_file(tmp_path: Path) -> None:
    document = tmp_path / "document.txt"
    document.write_text("needle first page " + "padding " * 10 + "needle last page", encoding="utf-8")
    browser = MarkdownFileBrowser(viewport_size=20, base_path=str(tmp_path), cwd=str(tmp_path))
    browser.open_path(str(document))
    assert browser.find_on_page("needle") is not None
    assert browser.viewport_current_page == 0
    assert browser.find_next() is not None
    assert browser.viewport_current_page > 0
    assert browser.find_next() is not None
    assert browser.viewport_current_page == 0
