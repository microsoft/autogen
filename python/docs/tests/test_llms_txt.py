"""Tests for the llms_txt Sphinx extension.

These tests verify that the extension correctly generates the llms.txt and
llms-full.txt files from a minimal Sphinx environment.
"""

import importlib.util
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Load the extension module by file path (no sys.path modification needed).
# ---------------------------------------------------------------------------

_EXT_FILE = Path(__file__).parent.parent / "src" / "_extension" / "llms_txt.py"
_spec = importlib.util.spec_from_file_location("_ext_llms_txt", _EXT_FILE)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

_build_llms_txt = _mod._build_llms_txt
_build_llms_full_txt = _mod._build_llms_full_txt
_page_content = _mod._page_content
_page_description = _mod._page_description
_page_title = _mod._page_title
_page_url = _mod._page_url
generate_llms_txt = _mod.generate_llms_txt

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app(
    *,
    html_baseurl: str = "https://example.com/autogen/dev",
    llms_txt_base_url: Optional[str] = None,
    llms_txt_sections: Optional[Dict[str, str]] = None,
    llms_txt_description: Optional[str] = None,
    project: str = "AutoGen",
    html_title: Optional[str] = None,
    found_docs: Any = None,
    titles: Any = None,
    metadata: Any = None,
) -> MagicMock:
    """Return a minimal mock Sphinx app with the given attributes."""
    from sphinx.builders.html import StandaloneHTMLBuilder

    if found_docs is None:
        found_docs = set()
    if titles is None:
        titles = {}
    if metadata is None:
        metadata = {}

    app = MagicMock()
    app.config.html_baseurl = html_baseurl
    # Explicitly set every config value so MagicMock doesn't return a truthy
    # MagicMock instance when the value should be None/falsy.
    app.config.llms_txt_base_url = llms_txt_base_url
    app.config.llms_txt_sections = llms_txt_sections
    app.config.llms_txt_description = llms_txt_description
    app.config.project = project
    app.config.html_title = html_title
    app.outdir = "/tmp/test-docs-out"

    # Builder must be an instance of StandaloneHTMLBuilder for the hook to fire
    app.builder = MagicMock(spec=StandaloneHTMLBuilder)
    app.builder.get_target_uri.side_effect = lambda docname: f"{docname}.html"

    # Sphinx environment
    app.env.found_docs = found_docs
    app.env.titles = titles
    app.env.metadata = metadata

    return app


def _title_node(text: str) -> Any:
    """Return a minimal docutils title node with the given text."""
    from docutils import nodes

    node = nodes.title()
    node += nodes.Text(text)
    return node


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------


def test_page_url_basic() -> None:
    app = _make_app(html_baseurl="https://docs.example.com/dev")
    url = _page_url(app, "user-guide/core-user-guide/index")
    assert url == "https://docs.example.com/dev/user-guide/core-user-guide/index.html"


def test_page_url_strips_trailing_slash() -> None:
    app = _make_app(html_baseurl="https://docs.example.com/dev/")
    url = _page_url(app, "user-guide/core-user-guide/installation")
    assert url == "https://docs.example.com/dev/user-guide/core-user-guide/installation.html"


def test_page_url_uses_llms_txt_base_url_over_html_baseurl() -> None:
    """When llms_txt_base_url is set it takes priority over html_baseurl."""
    app = _make_app(
        html_baseurl="/autogen/dev/",
        llms_txt_base_url="https://microsoft.github.io/autogen/dev",
    )
    url = _page_url(app, "user-guide/core-user-guide/index")
    assert url.startswith("https://microsoft.github.io/autogen/dev/")


def test_page_url_warns_when_root_relative(caplog: pytest.LogCaptureFixture) -> None:
    """A warning must be logged when the resolved base URL is root-relative."""
    app = _make_app(html_baseurl="/autogen/dev/", llms_txt_base_url=None)
    with caplog.at_level(logging.WARNING):
        url = _page_url(app, "user-guide/core-user-guide/index")
    assert "not absolute" in caplog.text
    assert url == "/autogen/dev/user-guide/core-user-guide/index.html"


def test_page_url_no_warning_for_absolute_url(caplog: pytest.LogCaptureFixture) -> None:
    """No warning should be emitted when the base URL is absolute."""
    app = _make_app(html_baseurl="https://docs.example.com/dev")
    with caplog.at_level(logging.WARNING):
        _page_url(app, "user-guide/core-user-guide/index")
    assert "not absolute" not in caplog.text


def test_page_title_present() -> None:
    docname = "user-guide/core-user-guide/index"
    app = _make_app(titles={docname: _title_node("Core User Guide")})
    assert _page_title(app, docname) == "Core User Guide"


def test_page_title_missing() -> None:
    app = _make_app(titles={})
    assert _page_title(app, "nonexistent") is None


def test_page_description_from_myst_html_meta() -> None:
    docname = "user-guide/agentchat-user-guide/index"
    metadata = {
        docname: {
            "myst": {
                "html_meta": {
                    "description lang=en": "AgentChat description here."
                }
            }
        }
    }
    app = _make_app(metadata=metadata)
    desc = _page_description(app, docname)
    assert desc == "AgentChat description here."


def test_page_description_missing() -> None:
    app = _make_app(metadata={})
    assert _page_description(app, "any-doc") is None


def test_page_description_collapses_whitespace() -> None:
    docname = "user-guide/core-user-guide/index"
    metadata = {
        docname: {
            "myst": {
                "html_meta": {
                    "description lang=en": "  Line one\n  line two.  "
                }
            }
        }
    }
    app = _make_app(metadata=metadata)
    desc = _page_description(app, docname)
    assert desc == "Line one line two."


def test_page_content_extracts_text_from_html(tmp_path: Path) -> None:
    """_page_content must return text inside <article>, excluding <nav>."""
    docname = "user-guide/core-user-guide/index"
    html = (
        "<html><body>"
        "<nav>Navigation</nav>"
        "<article><h1>Core</h1><p>Core overview text.</p></article>"
        "</body></html>"
    )
    html_file = tmp_path / "user-guide" / "core-user-guide" / "index.html"
    html_file.parent.mkdir(parents=True, exist_ok=True)
    html_file.write_text(html, encoding="utf-8")

    app = _make_app(found_docs={docname}, titles={docname: _title_node("Core")})
    app.outdir = str(tmp_path)

    text = _page_content(app, docname)
    assert text is not None
    assert "Core overview text." in text
    assert "Navigation" not in text


def test_page_content_returns_none_for_missing_file() -> None:
    """_page_content must return None when the HTML file does not exist."""
    app = _make_app()
    app.outdir = "/nonexistent/path"
    assert _page_content(app, "user-guide/core-user-guide/index") is None


# ---------------------------------------------------------------------------
# Integration-style tests for the full llms.txt content
# ---------------------------------------------------------------------------


def test_build_llms_txt_contains_required_sections() -> None:
    """Generated llms.txt must start with an H1 heading and include H2 sections."""
    found_docs = {
        "user-guide/core-user-guide/index",
        "user-guide/core-user-guide/installation",
        "user-guide/agentchat-user-guide/index",
        "user-guide/autogenstudio-user-guide/index",
        "user-guide/extensions-user-guide/index",
    }
    titles = {docname: _title_node(docname.split("/")[-1].replace("-", " ").title()) for docname in found_docs}
    app = _make_app(found_docs=found_docs, titles=titles)

    content = _build_llms_txt(app)

    assert content.startswith("# AutoGen"), "llms.txt must start with '# AutoGen'"
    assert "## Core" in content
    assert "## AgentChat" in content
    assert "## AutoGen Studio" in content
    assert "## Extensions" in content


def test_build_llms_txt_uses_html_title() -> None:
    """The H1 heading should use html_title when set."""
    app = _make_app(html_title="My Project Docs", project="MyProject")
    content = _build_llms_txt(app)
    assert content.startswith("# My Project Docs")


def test_build_llms_txt_falls_back_to_project_for_title() -> None:
    """The H1 heading should fall back to project when html_title is not set."""
    app = _make_app(html_title=None, project="FallbackProject")
    content = _build_llms_txt(app)
    assert content.startswith("# FallbackProject")


def test_build_llms_txt_uses_llms_txt_description() -> None:
    """When llms_txt_description is set, the blockquote must use it."""
    app = _make_app(
        llms_txt_description="Custom description for the project.",
        found_docs=set(),
        titles={},
    )
    content = _build_llms_txt(app)
    assert "> Custom description for the project." in content


def test_build_llms_txt_description_fallback_to_project() -> None:
    """When llms_txt_description is not set, the project name is the blockquote."""
    app = _make_app(project="MyProject", found_docs=set(), titles={})
    content = _build_llms_txt(app)
    assert "> MyProject" in content


def test_build_llms_txt_uses_configured_sections() -> None:
    """When llms_txt_sections is set, only those sections appear in the output."""
    custom_sections = {"My Section": "custom/path"}
    docname = "custom/path/page"
    app = _make_app(
        llms_txt_sections=custom_sections,
        found_docs={docname},
        titles={docname: _title_node("My Page")},
    )
    content = _build_llms_txt(app)
    assert "## My Section" in content
    assert "## Core" not in content
    assert "## AgentChat" not in content


def test_build_llms_txt_blockquote_format() -> None:
    """Every blockquote line in the summary must start with '> '."""
    app = _make_app(found_docs=set(), titles={})
    content = _build_llms_txt(app)

    blockquote_lines = [line for line in content.splitlines() if line.startswith(">")]
    assert blockquote_lines, "No blockquote lines found in llms.txt"
    for line in blockquote_lines:
        assert line.startswith("> "), f"Blockquote line does not start with '> ': {line!r}"


def test_build_llms_txt_links_use_base_url() -> None:
    """Every link in llms.txt must use the configured html_baseurl."""
    docname = "user-guide/core-user-guide/installation"
    app = _make_app(
        html_baseurl="https://microsoft.github.io/autogen/dev",
        found_docs={docname},
        titles={docname: _title_node("Installation")},
    )

    content = _build_llms_txt(app)
    assert "https://microsoft.github.io/autogen/dev/" in content


def test_build_llms_txt_links_use_llms_txt_base_url() -> None:
    """When llms_txt_base_url is set, links must use that value."""
    docname = "user-guide/core-user-guide/installation"
    app = _make_app(
        html_baseurl="/autogen/dev/",
        llms_txt_base_url="https://microsoft.github.io/autogen/dev",
        found_docs={docname},
        titles={docname: _title_node("Installation")},
    )

    content = _build_llms_txt(app)
    assert "https://microsoft.github.io/autogen/dev/" in content
    assert content.count("/autogen/dev/") == content.count("https://microsoft.github.io/autogen/dev/"), (
        "Root-relative prefix must not appear in llms.txt when llms_txt_base_url is set"
    )


def test_build_llms_txt_includes_description_when_available() -> None:
    """Links with a description should use the ': description' format."""
    docname = "user-guide/core-user-guide/index"
    metadata = {
        docname: {
            "myst": {
                "html_meta": {"description lang=en": "Core overview."}
            }
        }
    }
    app = _make_app(
        found_docs={docname},
        titles={docname: _title_node("Core")},
        metadata=metadata,
    )

    content = _build_llms_txt(app)
    assert "Core overview." in content


def test_build_llms_txt_skips_docs_without_title() -> None:
    """Pages without a Sphinx title node must be omitted from llms.txt."""
    docname = "user-guide/core-user-guide/installation"
    app = _make_app(found_docs={docname}, titles={})  # no title for this doc

    content = _build_llms_txt(app)
    # The document URL should not appear because the title is missing
    assert "installation.html" not in content


def test_build_llms_full_txt_contains_index(tmp_path: Path) -> None:
    """llms-full.txt must begin with the same index as llms.txt."""
    docname = "user-guide/core-user-guide/index"
    app = _make_app(found_docs={docname}, titles={docname: _title_node("Core")})
    app.outdir = str(tmp_path)

    full_content = _build_llms_full_txt(app)
    index_content = _build_llms_txt(app)
    assert full_content.startswith(index_content)


def test_build_llms_full_txt_appends_page_content(tmp_path: Path) -> None:
    """llms-full.txt must include the body text of each page when available."""
    docname = "user-guide/core-user-guide/index"
    html = "<html><body><article><p>Core page body text.</p></article></body></html>"
    html_file = tmp_path / "user-guide" / "core-user-guide" / "index.html"
    html_file.parent.mkdir(parents=True, exist_ok=True)
    html_file.write_text(html, encoding="utf-8")

    app = _make_app(found_docs={docname}, titles={docname: _title_node("Core")})
    app.outdir = str(tmp_path)

    full_content = _build_llms_full_txt(app)
    assert "Core page body text." in full_content


def test_build_llms_full_txt_omits_content_when_file_missing(tmp_path: Path) -> None:
    """llms-full.txt must not error when an HTML file is absent; just skip content."""
    docname = "user-guide/core-user-guide/index"
    app = _make_app(found_docs={docname}, titles={docname: _title_node("Core")})
    app.outdir = str(tmp_path)  # no HTML files created

    full_content = _build_llms_full_txt(app)
    # Index must be present, but no per-page URL/body block should appear
    assert "# AutoGen" in full_content
    assert "URL:" not in full_content  # URL: lines only appear in content blocks


def test_generate_llms_txt_writes_both_files(tmp_path: Path) -> None:
    """generate_llms_txt must write both llms.txt and llms-full.txt to app.outdir."""
    docname = "user-guide/agentchat-user-guide/index"
    app = _make_app(
        found_docs={docname},
        titles={docname: _title_node("AgentChat")},
    )
    app.outdir = str(tmp_path)

    generate_llms_txt(app, exception=None)

    assert (tmp_path / "llms.txt").exists(), "llms.txt was not created"
    assert (tmp_path / "llms-full.txt").exists(), "llms-full.txt was not created"
    assert "# AutoGen" in (tmp_path / "llms.txt").read_text(encoding="utf-8")
    assert "# AutoGen" in (tmp_path / "llms-full.txt").read_text(encoding="utf-8")


def test_generate_llms_txt_skips_on_exception(tmp_path: Path) -> None:
    """generate_llms_txt must be a no-op when an exception is passed."""
    app = _make_app()
    app.outdir = str(tmp_path)

    generate_llms_txt(app, exception=RuntimeError("build failed"))

    assert not (tmp_path / "llms.txt").exists()
    assert not (tmp_path / "llms-full.txt").exists()


def test_generate_llms_txt_skips_non_html_builder(tmp_path: Path) -> None:
    """generate_llms_txt must be a no-op for non-HTML builders."""
    from sphinx.builders import Builder

    docname = "user-guide/core-user-guide/index"
    app = _make_app(found_docs={docname}, titles={docname: _title_node("Core")})
    app.outdir = str(tmp_path)
    # Replace the HTML builder mock with a generic Builder mock
    app.builder = MagicMock(spec=Builder)

    generate_llms_txt(app, exception=None)

    assert not (tmp_path / "llms.txt").exists()
    assert not (tmp_path / "llms-full.txt").exists()
