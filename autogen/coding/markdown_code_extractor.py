import re
from typing import Any, Dict, List, Optional, Union

from ..code_utils import CODE_BLOCK_PATTERN, UNKNOWN, content_str, infer_lang
from ..types import UserMessageImageContentPart, UserMessageTextContentPart
from .base import CodeBlock, CodeExtractor

__all__ = ("MarkdownCodeExtractor",)


class MarkdownCodeExtractor(CodeExtractor):
    """(Experimental) A class that extracts code blocks from a message using Markdown syntax."""

    def extract_code_blocks(
        self, message: Union[str, List[Union[UserMessageTextContentPart, UserMessageImageContentPart]], None]
    ) -> List[CodeBlock]:
        """(Experimental) Extract code blocks from a message. If no code blocks are found,
        return an empty list.

        Args:
            message (str): The message to extract code blocks from.

        Returns:
            List[CodeBlock]: The extracted code blocks or an empty list.
        """

        text = content_str(message)
        match = re.findall(CODE_BLOCK_PATTERN, text, flags=re.DOTALL)
        if not match:
            return []
        code_blocks = []
        for lang, code in match:
            if lang == "":
                lang = infer_lang(code)
            if lang == UNKNOWN:
                lang = ""
            code_blocks.append(CodeBlock(code=code, language=lang))
        return code_blocks
