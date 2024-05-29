# File based from: https://github.com/microsoft/autogen/blob/main/autogen/coding/markdown_code_extractor.py
# Credit to original authors

import re
from typing import List

from .._base import CodeBlock, CodeExtractor
from .utils import CODE_BLOCK_PATTERN, infer_lang

__all__ = ("MarkdownCodeExtractor",)


class MarkdownCodeExtractor(CodeExtractor):
    """(Experimental) A class that extracts code blocks from a message using Markdown syntax."""

    def extract_code_blocks(self, message: str) -> List[CodeBlock]:
        """(Experimental) Extract code blocks from a message. If no code blocks are found,
        return an empty list.

        Args:
            message (str): The message to extract code blocks from.

        Returns:
            List[CodeBlock]: The extracted code blocks or an empty list.
        """

        match = re.findall(CODE_BLOCK_PATTERN, message, flags=re.DOTALL)
        if not match:
            return []
        code_blocks: List[CodeBlock] = []
        for lang, code in match:
            if lang == "":
                lang = infer_lang(code)
            if lang == "unknown":
                lang = ""
            code_blocks.append(CodeBlock(code=code, language=lang))
        return code_blocks
