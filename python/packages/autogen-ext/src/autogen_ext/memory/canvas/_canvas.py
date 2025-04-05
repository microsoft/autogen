import difflib
from typing import Dict, List


class FileRevision:
    """Tracks the history of one file's content."""

    def __init__(self, content: str, revision: int) -> None:
        self.content = content
        self.revision = revision  # e.g. an integer, a timestamp, or git hash


class Canvas:
    """
    A simple in-memory 'Canvas' that can store multiple named files, each with revision history.
    Allows retrieving content, generating diffs, and applying patches.
    """

    def __init__(self):
        # For each file, maintain a list of FileRevision. The latest revision is the end of the list.
        self._files: Dict[str, List[FileRevision]] = {}

    def _get_latest_revision_index(self, filename: str) -> int:
        return len(self._files.get(filename, [])) - 1

    def get_latest_content(self, filename: str) -> str:
        """
        Returns the latest version of the file content, or empty if not found.
        """
        revs = self._files.get(filename, [])
        if not revs:
            return ""
        return revs[-1].content

    def add_or_update_file(self, filename: str, new_content: str) -> None:
        """
        Overwrites the file with new_content, increments the revision index by 1.
        """
        if filename not in self._files:
            self._files[filename] = [FileRevision(new_content, 1)]
        else:
            current_revs = self._files[filename]
            last_rev = current_revs[-1].revision
            current_revs.append(FileRevision(new_content, last_rev + 1))

    def get_diff(self, filename: str, from_revision: int, to_revision: int) -> str:
        """
        Returns a unified diff (string) between two revisions of the same file.
        """
        revisions = self._files.get(filename, [])
        # naive checks
        if not revisions or to_revision <= 0 or from_revision <= 0:
            return ""
        from_content = ""
        to_content = ""
        for rev in revisions:
            if rev.revision == from_revision:
                from_content = rev.content
            elif rev.revision == to_revision:
                to_content = rev.content

        diff = difflib.unified_diff(
            from_content.splitlines(keepends=True),
            to_content.splitlines(keepends=True),
            fromfile=f"{filename}@r{from_revision}",
            tofile=f"{filename}@r{to_revision}",
        )
        return "".join(diff)

    def apply_patch(self, filename: str, patch_text: str) -> None:
        """
        Applies a unified diff patch to the latest version of a file and saves as a new revision.
        """
        # We retrieve the latest content, apply patch line by line.
        current_content = self.get_latest_content(filename)
        patched_lines = []
        # difflib.patch.diff_bytes or external libs can do more robust patching. This is
        # a simplified approach to illustrate the concept:
        patched = difflib.restore(patch_text.splitlines(keepends=True), 2)
        # difflib.restore expects a certain format that matches a 'context diff' or 'unified diff'
        # If you want a robust patch apply, consider `unidiff` library or a real VCS-based approach.
        patched_lines = list(patched)

        new_content = "".join(patched_lines)
        self.add_or_update_file(filename, new_content)

    def list_files(self) -> Dict[str, int]:
        """
        Returns a dict of filename -> latest revision number.
        """
        results = {}
        for fname, revs in self._files.items():
            if revs:
                results[fname] = revs[-1].revision
        return results

    def get_all_contents_for_context(self) -> str:
        """
        Quick way to produce a text block summarizing the entire canvas and its latest revisions
        for LLM consumption.
        """
        out = ["=== CANVAS FILES ==="]
        for fname, revs in self._files.items():
            latest_rev = revs[-1]
            out.append(f"File: {fname} (rev {latest_rev.revision}):\n{latest_rev.content}\n")
        out.append("=== END OF CANVAS ===")
        return "\n".join(out)
