import difflib

from autogen_ext.memory.canvas import TextCanvas


def test_get_diff_rejects_unknown_revision() -> None:
    """An unknown revision id must return an empty diff.

    Revision existence used to be inferred from the revision *content* being
    empty, so a request for a revision id that never existed was silently
    treated as "empty file" and produced a full diff instead of no diff.
    """
    canvas = TextCanvas()
    canvas.add_or_update_file("notes.md", "")  # revision 1: content is legitimately empty
    canvas.add_or_update_file("notes.md", "hello\n")  # revision 2

    # Revision 999 does not exist, so there is nothing to compare.
    assert canvas.get_diff("notes.md", 999, 2) == ""

    # Revision 1 does exist and is genuinely empty, so it must still be diffed.
    expected = "".join(
        difflib.unified_diff(
            "".splitlines(keepends=True),
            "hello\n".splitlines(keepends=True),
            fromfile="notes.md@r1",
            tofile="notes.md@r2",
        )
    )
    assert canvas.get_diff("notes.md", 1, 2) == expected
