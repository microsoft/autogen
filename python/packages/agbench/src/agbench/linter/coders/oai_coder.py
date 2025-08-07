import os
import re
from typing import List, Optional, Set

from openai import OpenAI
from pydantic import BaseModel

from .._base import BaseQualitativeCoder, Code, CodedDocument, CodeExample, Document
from ._prompt import MAIN_PROMPT


class CodeList(BaseModel):
    code_list: List[Code]


def remove_control_characters(text: str) -> str:
    """
    Remove control characters from the text.
    """
    return re.sub(r"[\x00-\x1F\x7F]", "", text)


class OAIQualitativeCoder(BaseQualitativeCoder):
    DEFAULT_MODEL = "gpt-4o"
    MAIN_PROMPT = MAIN_PROMPT

    def __init__(self, cache_dir: str = ".cache", model: str = DEFAULT_MODEL, cache_enabled: bool = False) -> None:
        self.client = OpenAI()
        self.cache_dir = cache_dir
        self.model = model
        self.cache_enabled = cache_enabled

    def code_document(self, doc: Document, code_set: Optional[Set[Code]] = None) -> Optional[CodedDocument]:
        coded_doc = self._code_document(doc)
        if coded_doc is None:
            raise ValueError("Error in coding document with OpenAI")

        feedback = self._reflect_on_codes(coded_doc)

        coded_doc = self._code_document_with_feedback(coded_doc, feedback)

        if coded_doc is None:
            raise ValueError("Error in coding document with OpenAI")

        feedback = self._reflect_on_codes(coded_doc)

        coded_doc = self._code_document_with_feedback(coded_doc, feedback)

        return coded_doc

    def _code_document_with_feedback(self, coded_doc: CodedDocument, feedback: str) -> Optional[CodedDocument]:
        """
        Given a coded document and feedback, update the codes in the document.

        Again uses completion to generate new code lists
        based on the doc, original codes, and feedback.
        """

        prompt = self.MAIN_PROMPT

        prompt += "\nDocument:\n"
        for line in coded_doc.doc.lines:
            prompt += f"{line}"
        prompt += "Notice that the document contains the following number of lines: "
        prompt += str(len(coded_doc.doc.lines))

        prompt += "\n\n"

        prompt += "A previous attempt to code the document resulted in the following codes:\n"
        for code in coded_doc.codes:
            prompt += code.model_dump_json(indent=4)
            prompt += "\n"
        prompt += "\n\n"

        prompt += "A human expert has provided the following feedback on the codes:\n"
        prompt += f"{feedback}\n\n"

        prompt += "Now revise the codes based on the feedback. "

        # save coding with feedback prompt to a file
        # with open("coding_with_feedback_prompt.txt", "w") as f:
        #     f.write(prompt)

        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format=CodeList,
        )
        message = completion.choices[0].message
        if message.parsed and len(message.parsed.code_list) > 0:
            coded_doc.codes = set(message.parsed.code_list)
        else:
            print(message.refusal)
            raise ValueError("Error in coding document with OpenAI")

        return coded_doc

    def _code_document(self, doc: Document) -> Optional[CodedDocument]:
        # get hash of the document
        doc_hash = hash(doc)
        cache_file = os.path.join(self.cache_dir, f"{doc_hash}.json") if self.cache_enabled else None

        if self.cache_enabled:
            if not os.path.exists(self.cache_dir):
                os.makedirs(self.cache_dir)
            if cache_file and os.path.exists(cache_file):
                with open(cache_file, "r") as f:
                    cached_coded_doc_json = f.read()
                    return CodedDocument.from_json(cached_coded_doc_json)

        # sanitize the doc before passing it to openai
        doc.text = remove_control_characters(doc.text)

        coded_document: Optional[CodedDocument] = None

        prompt = """You are an expert qualitative researcher.

Given a document containing errors below, generate a list of (error) codes.
The document shows a log of interaction between multiple agents collaborating
to solve a complex task.

Each code should contains:
- at least 3 words, max 4 word, hyphenated.

For example, the name could be of the format "lack-of-word2",
"failed-to-bar", "excessive-use-of-magenta". Name should adhere to
Joseph M. Williams' writing principles of clarity, conciseness, and coherence.

Ensure each code name is lower-case, hyphenated, and directly reflects the
concept it represents. Avoid ambiguous or overly complex terms, and prioritize
simplicity, precision, and readability in the naming.

The code names should pass the 'clarity and grace' test by being easy to
understand, descriptive, and reflective of the content they categorize.
- suggest codes that are similar to good code names. avoid code names that are
similar to bad code names.
- The definition should be simple worded and practical. At least 2 sentences,
max 3. It should be written in past tense.

It should convey how a labeller could apply this code to future logs, without
mentioning the word "labeller". The definition should be specific enough to be
useful in debugging. It should be very concrete. And should be well thought and
make sense. Bull shitting will not earn you any points.

- The examples should be a list. Each example should be descriptive between
2-3 sentences. Examples should be concrete, informative and not vague. Provide
at max 20 salient examples. Examples should contain a lot of detail about what
happened and should refer to incidents in the log.

- The list of codes must mutually exclusive.

# GOOD EXAMPLES OF FINAL CODE NAMES/CLUSTERS
* looped-without-progress
* repeated-unsuccessful-actions
* repeated-syntax-errors
* exceeded-context-window-limits
* encountered-security-risks
* failure-to-switch-strategy
* exceeded-resource-limits
* attempted-to-handle-excessive-data
* no-errors-detected
These names are high-level but also concrete. They exactly mention the type of
error, issue, gap that has been identified.

## BAD EXAMPLES OF FINAL CODE NAMES/CLUSTERS
* mismanaged-data-utilization -- too high level
* incomplete-or-misguided-execution -- too high level
* misaligned-agent-interactions -- too high level
* mismanaged-task-strategies -- too high level
* resource-inefficiencies -- vague
* communication-issues -- vague
* coordination-issues -- too high level and vague
* operational-failures
* execution-errors -- too high level
* navigation-issues -- too concise
* adaptive-failures -- too concise
* successful-processes -- I dont like the word processes
* system-constraints
* configuration-issues
* information-inaccuracies -- too high level
* process-improvements -- vague, not an error
* inadequate-error-response -- too high-level, unclear what kind of errors
* specific-access-issues -- makes no sense
* strategy-inefficiency -- strategy is too high level
* error-management-gaps -- unclear what error management means
* error-handling-deficiency -- unclear what kind of errors
* coordination-breakdown -- unclear what coordination means
* muddled-task-execution -- unclear what kind of tasks were muddled
* task-completion-gaps -- too high level
The above names are too high level and unclear. Please DO NOT use such names.

Document:

"""

        for line in doc.lines:
            prompt += f"{line}"
        prompt += "\n\n"
        prompt += "Notice that the document contains the following number of lines: "
        prompt += str(len(doc.lines))
        prompt += "\n\n"

        prompt += (
            "Now generate a list of codes for the document."
            " Especially codes that detect errors/inefficiencies in the document."
        )

        # save the coding prompt to a file
        # with open("coding_prompt.txt", "w") as f:
        #     f.write(prompt)

        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            response_format=CodeList,
        )

        message = completion.choices[0].message
        if message.parsed and len(message.parsed.code_list) > 0:
            coded_document = CodedDocument(doc=doc, codes=set(message.parsed.code_list))
        else:
            print(message.refusal)
            raise ValueError("Error in coding document with OpenAI")

        if self.cache_enabled and cache_file:
            with open(cache_file, "w") as f:
                f.write(coded_document.model_dump_json(indent=4))

        return coded_document

    def _codes_to_string(self, codes: Set[Code]) -> str:
        """
        Convert a set of codes to a string representation.
        Include name, definition, examples, line number, and severity.
        """
        code_list: List[str] = []
        for code in codes:
            code_list.append(f"[{code.severity}]: {code.name}: {code.definition}")
            for example in code.examples:
                code_list.append(f"\t{example.line}:{example.line_end}\t{example.reason}")
        return "\n".join(code_list)

    def _extract_lines(self, doc: Document, start: int, end: int, buffer: int = 1) -> str:
        """
        Extract a line from the document.
        """
        start_line = max(0, start - buffer)
        end_line = min(len(doc.lines), end + buffer)
        lines = doc.lines[start_line:end_line]
        return "".join(lines)

    def _extract_code_lines(self, doc: Document, example: CodeExample) -> str:
        """
        Extract lines from the document based on the code.
        """
        start = example.line
        end = example.line_end
        lines = self._extract_lines(doc, start, end)
        return lines

    def _reflect_on_codes(self, coded_doc: CodedDocument) -> str:
        """
        Given a coded document generate feedback.
        E.g., whether the code used seem appropriate or not.
        """

        prompt = (
            "You are an expert qualitative researcher. "
            "You are given a list of codes. "
            "Pay attention the codes and the lines mentioned in the examples of the codes. "
            "Which examples fail to spot meaningful errors? "
            "Be direct and critical. "
            "If a code identifies a BS error, say it. "
            "There is no need to figure out how to fix the actual error. "
            "The goal is to double check the validity of detected errors.\n\n"
        )

        # for line in coded_doc.doc.lines:
        #     prompt += f"{line}"
        # prompt += "\n\n"

        # prompt += "Notice that the document contains the following number of lines: "
        # prompt += str(len(coded_doc.doc.lines))

        # prompt += "\n\n"
        prompt += "A qualitative coding of a document claims to spot the following errors:\n\n"
        for code in coded_doc.codes:
            prompt += f"Code: {code.name}\n"
            prompt += f"Definition: {code.definition}\n"
            prompt += "Examples:\n"
            for example in code.examples:
                extracted_lines = self._extract_code_lines(coded_doc.doc, example)
                prompt += f"- Does the text in the lines {example.line}:{example.line_end} shown below have enough information to justify the {code.name} error? "
                prompt += f"Especially does the line {example.line} contain the error?\n\n"
                prompt += f"{extracted_lines}\n"
                prompt += "\n\n"
            prompt += "\n"

        prompt += (
            "Now carefully analyze the examples. And provide feedback on the codes."
            "If the examples lines do not align with the code name or definition, provide feedback."
        )

        # save the reflection_prompt to a file
        # with open("reflection_prompt.txt", "w") as f:
        #     f.write(prompt)

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )

        feedback = completion.choices[0].message.content
        if feedback is None:
            raise ValueError("Error in generating feedback with OpenAI")
        return feedback
