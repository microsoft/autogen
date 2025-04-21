import difflib
from typing import Any, Dict, List, Union

try:  # pragma: no cover
    from unidiff import PatchSet
except ModuleNotFoundError:  # pragma: no cover
    PatchSet = None  # type: ignore

from ._canvas import BaseCanvas


class FileRevision:
    """Tracks the history of one file's content."""

    __slots__ = ("content", "revision")

    def __init__(self, content: str, revision: int) -> None:
        self.content: str = content
        self.revision: int = revision  # e.g. an integer, a timestamp, or git hash


class TextCanvas(BaseCanvas):
    """An in‑memory canvas that stores *text* files with full revision history.

    ... warning::

        This is an experimental API and may change in the future.

    Besides the original CRUD‑like operations, this enhanced implementation adds:

    * **apply_patch** – applies patches using the ``unidiff`` library for accurate
      hunk application and context line validation.
    * **get_revision_content** – random access to any historical revision.
    * **get_revision_diffs** – obtain the list of diffs applied between every
      consecutive pair of revisions so that a caller can replay or audit the
      full change history.
    """

    # ----------------------------------------------------------------------------------
    # Construction helpers
    # ----------------------------------------------------------------------------------

    def __init__(self) -> None:
        # For each file we keep an *ordered* list of FileRevision where the last
        # element is the most recent.  Using a list keeps the memory footprint
        # small and preserves order without any extra bookkeeping.
        self._files: Dict[str, List[FileRevision]] = {}

    # ----------------------------------------------------------------------------------
    # Internal utilities
    # ----------------------------------------------------------------------------------

    def _latest_idx(self, filename: str) -> int:
        """Return the index (not revision number) of the newest revision."""
        return len(self._files.get(filename, [])) - 1

    def _ensure_file(self, filename: str) -> None:
        if filename not in self._files:
            raise ValueError(f"File '{filename}' does not exist on the canvas; create it first.")

    # ----------------------------------------------------------------------------------
    # Revision inspection helpers
    # ----------------------------------------------------------------------------------

    def get_revision_content(self, filename: str, revision: int) -> str:  # NEW 🚀
        """Return the exact content stored in *revision*.

        If the revision does not exist an empty string is returned so that
        downstream code can handle the "not found" case without exceptions.
        """
        for rev in self._files.get(filename, []):
            if rev.revision == revision:
                return rev.content
        return ""

    def get_revision_diffs(self, filename: str) -> List[str]:  # NEW 🚀
        """Return a *chronological* list of unified‑diffs for *filename*.

        Each element in the returned list represents the diff that transformed
        revision *n* into revision *n+1* (starting at revision 1 → 2).
        """
        revisions = self._files.get(filename, [])
        diffs: List[str] = []
        for i in range(1, len(revisions)):
            older, newer = revisions[i - 1], revisions[i]
            diff = difflib.unified_diff(
                older.content.splitlines(keepends=True),
                newer.content.splitlines(keepends=True),
                fromfile=f"{filename}@r{older.revision}",
                tofile=f"{filename}@r{newer.revision}",
            )
            diffs.append("".join(diff))
        return diffs

    # ----------------------------------------------------------------------------------
    # BaseCanvas interface implementation
    # ----------------------------------------------------------------------------------

    def list_files(self) -> Dict[str, int]:
        """Return a mapping of *filename → latest revision number*."""
        return {fname: revs[-1].revision for fname, revs in self._files.items() if revs}

    def get_latest_content(self, filename: str) -> str:  # noqa: D401 – keep API identical
        """Return the most recent content or an empty string if the file is new."""
        revs = self._files.get(filename, [])
        return revs[-1].content if revs else ""

    def add_or_update_file(self, filename: str, new_content: Union[str, bytes, Any]) -> None:
        """Create *filename* or append a new revision containing *new_content*."""
        if isinstance(new_content, bytes):
            new_content = new_content.decode("utf-8")
        if not isinstance(new_content, str):
            raise ValueError(f"Expected str or bytes, got {type(new_content)}")
        if filename not in self._files:
            self._files[filename] = [FileRevision(new_content, 1)]
        else:
            last_rev_num = self._files[filename][-1].revision
            self._files[filename].append(FileRevision(new_content, last_rev_num + 1))

    def get_diff(self, filename: str, from_revision: int, to_revision: int) -> str:
        """Return a unified diff between *from_revision* and *to_revision*."""
        revisions = self._files.get(filename, [])
        if not revisions:
            return ""
        # Fetch the contents for the requested revisions.
        from_content = self.get_revision_content(filename, from_revision)
        to_content = self.get_revision_content(filename, to_revision)
        if from_content == "" and to_content == "":  # one (or both) revision ids not found
            return ""
        diff = difflib.unified_diff(
            from_content.splitlines(keepends=True),
            to_content.splitlines(keepends=True),
            fromfile=f"{filename}@r{from_revision}",
            tofile=f"{filename}@r{to_revision}",
        )
        return "".join(diff)

    def apply_patch(self, filename: str, patch_data: Union[str, bytes, Any]) -> None:
        """Apply *patch_text* (unified diff) to the latest revision and save a new revision.

        Uses the *unidiff* library to accurately apply hunks and validate context lines.
        """
        if isinstance(patch_data, bytes):
            patch_data = patch_data.decode("utf-8")
        if not isinstance(patch_data, str):
            raise ValueError(f"Expected str or bytes, got {type(patch_data)}")
        self._ensure_file(filename)
        original_content = self.get_latest_content(filename)

        if PatchSet is None:
            raise ImportError(
                "The 'unidiff' package is required for patch application. Install with 'pip install unidiff'."
            )

        patch = PatchSet(patch_data)
        # Our canvas stores exactly one file per patch operation so we
        # use the first (and only) patched_file object.
        if not patch:
            raise ValueError("Empty patch text provided.")
        patched_file = patch[0]
        working_lines = original_content.splitlines(keepends=True)
        line_offset = 0
        for hunk in patched_file:
            # Calculate the slice boundaries in the *current* working copy.
            start = hunk.source_start - 1 + line_offset
            end = start + hunk.source_length
            # Build the replacement block for this hunk.
            replacement: List[str] = []
            for line in hunk:
                if line.is_added or line.is_context:
                    replacement.append(line.value)
                # removed lines (line.is_removed) are *not* added.
            # Replace the slice with the hunk‑result.
            working_lines[start:end] = replacement
            line_offset += len(replacement) - (end - start)
        new_content = "".join(working_lines)

        # Finally commit the new revision.
        self.add_or_update_file(filename, new_content)

    # ----------------------------------------------------------------------------------
    # Convenience helpers
    # ----------------------------------------------------------------------------------

    def get_all_contents_for_context(self) -> str:  # noqa: D401 – keep public API stable
        """Return a summarised view of every file and its *latest* revision."""
        out: List[str] = ["=== CANVAS FILES ==="]
        for fname, revs in self._files.items():
            latest = revs[-1]
            out.append(f"File: {fname} (rev {latest.revision}):\n{latest.content}\n")
        out.append("=== END OF CANVAS ===")
        return "\n".join(out)
