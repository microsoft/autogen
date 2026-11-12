import difflib

import pytest
from autogen_core import CancellationToken
from autogen_core.model_context import UnboundedChatCompletionContext

from autogen_ext.memory.canvas import TextCanvasMemory
from autogen_ext.memory.canvas._canvas_writer import (
    ApplyPatchArgs,
    UpdateFileArgs,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────────
@pytest.fixture()
def story_v1() -> str:
    # Extracted (slightly trimmed) from the sample output
    return (
        "# The Bunny and the Sunflower\n\n"
        "## Beginning\n"
        "Once upon a time, in a bright and cheerful meadow, Bella the bunny came "
        "across **a beautiful sunflower** waving in the sunshine.\n"
    )


@pytest.fixture()
def story_v2(story_v1: str) -> str:
    # A small edit: give the sunflower a name (mirrors the first patch in the log)
    return story_v1.replace(
        "a beautiful sunflower",
        "a beautiful sunflower named Sunny",
    )


@pytest.fixture()
def memory() -> TextCanvasMemory:
    return TextCanvasMemory()


@pytest.fixture()
def config_v1() -> str:
    # Baseline content used by the stale-patch regression tests
    return "service=payments\nregion=Singapore\nstatus=active\n"


@pytest.fixture()
def config_v2() -> str:
    # A competing edit that changes the same line the stale patch targets
    return "service=payments\nregion=London\nstatus=active\n"


@pytest.fixture()
def config_v3() -> str:
    # A follow-up edit prepared against config_v2 (not against config_v1)
    return "service=payments\nregion=London\nstatus=retired\n"


def make_patch(old: str, new: str, filename: str = "state.txt") -> str:
    """Helper: build a unified diff between two contents (as the issue repro does)."""
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=filename,
            tofile=filename,
        )
    )


# ── Tests ────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_canvas_initial_state(memory: TextCanvasMemory) -> None:
    assert memory.canvas.list_files() == {}
    snapshot = memory.canvas.get_all_contents_for_context()
    assert snapshot.startswith("=== CANVAS FILES ===")


@pytest.mark.asyncio
async def test_update_file_tool_creates_file(
    memory: TextCanvasMemory,
    story_v1: str,
) -> None:
    update_tool = memory.get_update_file_tool()

    await update_tool.run(
        UpdateFileArgs(filename="story.md", new_content=story_v1),
        CancellationToken(),
    )

    assert memory.canvas.get_latest_content("story.md") == story_v1
    assert memory.canvas.list_files()["story.md"] == 1


@pytest.mark.asyncio
async def test_apply_patch_increments_revision(
    memory: TextCanvasMemory,
    story_v1: str,
    story_v2: str,
) -> None:
    # Set up revision 1
    await memory.get_update_file_tool().run(
        UpdateFileArgs(filename="story.md", new_content=story_v1),
        CancellationToken(),
    )

    # Create a unified diff for the patch tool
    diff_text = "".join(
        difflib.unified_diff(
            story_v1.splitlines(keepends=True),
            story_v2.splitlines(keepends=True),
            fromfile="story.md",
            tofile="story.md",
        )
    )

    # Apply the patch → revision 2
    await memory.get_apply_patch_tool().run(
        ApplyPatchArgs(filename="story.md", patch_text=diff_text),
        CancellationToken(),
    )

    assert memory.canvas.get_latest_content("story.md") == story_v2
    # The revision number should now be 2
    assert memory.canvas.list_files()["story.md"] == 2
    # And the diff history should contain exactly one patch
    assert len(memory.canvas.get_revision_diffs("story.md")) == 1


@pytest.mark.asyncio
async def test_apply_patch_rejects_stale_hunks(
    memory: TextCanvasMemory,
    config_v1: str,
    config_v2: str,
    config_v3: str,
) -> None:
    # Regression test for the stale-patch bug: a patch prepared against an
    # older revision must not be applied to the latest revision.
    # Revision 1: the baseline content.
    await memory.get_update_file_tool().run(
        UpdateFileArgs(filename="state.txt", new_content=config_v1),
        CancellationToken(),
    )
    # A patch prepared against revision 1 (removes "region=Singapore").
    edit_from_v1 = "service=payments\nregion=Tokyo\nstatus=active\n"
    stale_patch = make_patch(config_v1, edit_from_v1)
    # Revision 2: a competing edit changes the same line to "region=London".
    await memory.get_update_file_tool().run(
        UpdateFileArgs(filename="state.txt", new_content=config_v2),
        CancellationToken(),
    )

    # Applying the stale patch must fail loudly ...
    with pytest.raises(ValueError, match="does not match the latest revision"):
        await memory.get_apply_patch_tool().run(
            ApplyPatchArgs(filename="state.txt", patch_text=stale_patch),
            CancellationToken(),
        )

    # ... and leave revision 2 as the latest, untouched content.
    assert memory.canvas.get_latest_content("state.txt") == config_v2
    assert memory.canvas.list_files()["state.txt"] == 2

    # Control: a patch prepared from the actual revision-2 content applies.
    result = await memory.get_apply_patch_tool().run(
        ApplyPatchArgs(filename="state.txt", patch_text=make_patch(config_v2, config_v3)),
        CancellationToken(),
    )
    assert result.status == "PATCH APPLIED"
    assert memory.canvas.get_latest_content("state.txt") == config_v3
    assert memory.canvas.list_files()["state.txt"] == 3


@pytest.mark.asyncio
async def test_apply_patch_rejects_near_miss_context(
    memory: TextCanvasMemory,
    config_v1: str,
) -> None:
    # A context line that differs from the current content by a single
    # character must still be rejected (no fuzzy matching).
    await memory.get_update_file_tool().run(
        UpdateFileArgs(filename="state.txt", new_content=config_v1),
        CancellationToken(),
    )
    # Patch prepared against content whose context differs slightly from the canvas.
    drifted = config_v1.replace("payments", "paymentz")
    near_miss_patch = make_patch(drifted, drifted.replace("active", "retired"))

    with pytest.raises(ValueError, match="does not match the latest revision"):
        await memory.get_apply_patch_tool().run(
            ApplyPatchArgs(filename="state.txt", patch_text=near_miss_patch),
            CancellationToken(),
        )

    assert memory.canvas.get_latest_content("state.txt") == config_v1
    assert memory.canvas.list_files()["state.txt"] == 1


@pytest.mark.asyncio
async def test_update_context_injects_snapshot(
    memory: TextCanvasMemory,
    story_v2: str,
) -> None:
    # Seed with some content
    await memory.get_update_file_tool().run(
        UpdateFileArgs(filename="story.md", new_content=story_v2),
        CancellationToken(),
    )

    chat_ctx = UnboundedChatCompletionContext()
    result = await memory.update_context(chat_ctx)

    # A single SystemMessage should have been added to the context
    assert len(chat_ctx._messages) == 1  # type: ignore
    injected_text = chat_ctx._messages[0].content  # type: ignore
    assert "=== CANVAS FILES ===" in injected_text
    assert "story.md" in injected_text

    # The UpdateContextResult should surface the same snapshot via MemoryContent
    assert result.memories.results
    assert isinstance(result.memories.results[0].content, str)
    assert story_v2.strip() in result.memories.results[0].content
