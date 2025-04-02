import re
from typing import List, Sequence

from autogen_core.code_executor import CodeBlock, CodeExecutor
from autogen_agentchat.agents import CodeExecutorAgent


class CustomCodeExecutorAgent(CodeExecutorAgent):

    def __init__(
        self,
        name: str,
        code_executor: CodeExecutor,
        *,
        description: str = "A computer terminal that performs no other action than running Python scripts (provided to it quoted in ```python code blocks), or sh shell scripts (provided to it quoted in ```sh code blocks).",
        sources: Sequence[str] | None = None,
    ) -> None:
        super().__init__(name=name, description=description, code_executor=code_executor, sources=sources)
        self._test_code = ""
        with open("test.txt", "rt") as fh:
            self._test_code = fh.read()


    def _extract_markdown_code_blocks(self, markdown_text: str) -> List[CodeBlock]:
        code_blocks = super()._extract_markdown_code_blocks(markdown_text)
        new_blocks: List[CodeBlock] = []
        for block in code_blocks:

            # Handle deepseek
            code_content = block.code
            #m = re.search(r"^\s*<think>\s*(.*?)\s*</think>\s*(.*?)\s*$", code_content, re.DOTALL)
            #if m:
            #    code_content = m.group(2)

            # If python, wrap the extracted code in a unit testing harness
            if block.language and block.language.lower() == "python":
                code_content = self._test_code + """

def run_tests(candidate):
    try:
        check(candidate)
        # We can search for this string in the output
        print("ALL TESTS PASSED !#!#")
        print("TERMINATE")
    except AssertionError:
        print("SOME TESTS FAILED - TRY AGAIN !#!#")

""" + code_content + """

run_tests(__ENTRY_POINT__)
"""
            new_blocks.append(CodeBlock(code=code_content, language=block.language))

        return new_blocks
