from typing import Any, Dict, List, Union

from ..code_utils import UNKNOWN, content_str, infer_lang
from .base import CodeBlock

from marko import Markdown
from marko.block import FencedCode
from marko.inline import RawText


__all__ = ("MarkdownCodeExtractor",)


class MarkdownCodeExtractor:
    """(Experimental) A class that extracts code blocks from a message using Markdown syntax."""

    def extract_code_blocks(self, message: Union[str, List[Dict[str, Any]], None]) -> List[CodeBlock]:
        """(Experimental) Extract code blocks from a message. If no code blocks are found,
        returns an empty list.

        Args:
            message (str): The message to extract code blocks from.

        Returns:
            List[CodeBlock]: The extracted code blocks or an empty list.
        """

        text = content_str(message)
        result = Markdown().parse(text)
        code_blocks = []
        for element in result.children:
            if isinstance(element, FencedCode):
                assert isinstance(element.children[0], RawText)
                assert isinstance(element.children[0].children, str)
                content = element.children[0].children
                lang = element.lang
                if lang == "":
                    lang = infer_lang(content)
                if lang == UNKNOWN:
                    lang = ""
                code_blocks.append(CodeBlock(code=content, language=lang))

        return code_blocks
