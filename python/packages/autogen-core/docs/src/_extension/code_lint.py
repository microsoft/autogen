# Modified from: https://github.com/kai687/sphinxawesome-codelinter

import tempfile
from typing import AbstractSet, Any, Iterable

from docutils import nodes
from sphinx.application import Sphinx
from sphinx.builders import Builder
from sphinx.util import logging
from sphinx.util.console import darkgreen, darkred, red, teal, faint  # type: ignore[attr-defined]

from pygments import highlight  # type: ignore
from pygments.lexers import PythonLexer
from pygments.formatters import TerminalFormatter

logger = logging.getLogger(__name__)

__version__ = "0.1.0"


class CodeLinter(Builder):
    """Iterate over all ``literal_block`` nodes.

    pipe them into any command line tool that
    can read from standard input.
    """

    name = "code_lint"
    allow_parallel = True

    def init(self) -> None:
        """Initialize."""
        self._had_errors = False
        pass

    def get_outdated_docs(self) -> str | Iterable[str]:
        """Check for outdated files.

        Return an iterable of outdated output files, or a string describing what an
        update will build.
        """
        return self.env.found_docs

    def get_target_uri(self, docname: str, typ: str | None = None) -> str:
        """Return Target URI for a document name."""
        return ""

    def prepare_writing(self, docnames: AbstractSet[str]) -> None:
        """Run these steps before documents are written."""
        return

    def write_doc(self, docname: str, doctree: nodes.Node) -> None:
        path_prefix: str = self.app.config.code_lint_path_prefix
        supported_languages = set(["python", "default"])

        if not docname.startswith(path_prefix):
            return

        for code in doctree.findall(nodes.literal_block):
            if code["language"] in supported_languages:
                logger.info("Checking a code block in %s...", docname, nonl=True)
                if "ignore" in code["classes"]:
                    logger.info(" " + darkgreen("OK[ignored]"))
                    continue

                # Create a temporary file to store the code block
                with tempfile.NamedTemporaryFile(mode="wb", suffix=".py") as temp_file:
                    temp_file.write(code.astext().encode())
                    temp_file.flush()

                    # Run pyright on the temporary file using subprocess.run
                    import subprocess

                    result = subprocess.run(["pyright", temp_file.name], capture_output=True, text=True)
                    if result.returncode != 0:
                        logger.info(" " + darkred("FAIL"))
                        highlighted_code = highlight(code.astext(), PythonLexer(), TerminalFormatter())  # type: ignore
                        output = f"{faint('========================================================')}\n{red('Error')}: Pyright found issues in {teal(docname)}:\n{faint('--------------------------------------------------------')}\n{highlighted_code}\n{faint('--------------------------------------------------------')}\n\n{teal('pyright output:')}\n{red(result.stdout)}{faint('========================================================')}\n"
                        logger.info(output)
                        self._had_errors = True
                    else:
                        logger.info(" " + darkgreen("OK"))

    def finish(self) -> None:
        """Finish the build process."""
        if self._had_errors:
            raise RuntimeError("Code linting failed - see earlier output")


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_builder(CodeLinter)
    app.add_config_value("code_lint_path_prefix", "", "env")

    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
