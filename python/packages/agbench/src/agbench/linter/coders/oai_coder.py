import os
import re
from typing import List, Optional, Set

from openai import OpenAI
from pydantic import BaseModel

from .._base import BaseQualitativeCoder, Code, CodedDocument, Document


class CodeList(BaseModel):
    code_list: List[Code]


def remove_control_characters(text: str) -> str:
    """
    Remove control characters from the text.
    """
    return re.sub(r"[\x00-\x1F\x7F]", "", text)


class OAIQualitativeCoder(BaseQualitativeCoder):
    DEFAULT_MODEL = "gpt-4o"

    def __init__(self, cache_dir: str = ".cache", model: str = DEFAULT_MODEL, cache_enabled: bool = False) -> None:
        self.client = OpenAI()
        self.cache_dir = cache_dir
        self.model = model
        self.cache_enabled = cache_enabled

    def code_document(
        self,
        doc: Document,
        code_set: Optional[Set[Code]] = None,
    ) -> Optional[CodedDocument]:
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

        if code_set is None:
            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert qualitative researcher.

Given a list of dcocuments containing errors below, generate a list of (error) codes.
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
    """,
                    },
                    {
                        "role": "user",
                        "content": doc.text,
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
        else:
            code_to_str = "\n".join(
                [
                    (
                        f"\n---\nCode Name: {code.name}\n"
                        f"Definition: {code.definition}\n"
                        f"Examples: {code.examples}\n---\n"
                    )
                    for code in code_set
                ]
            )

            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert qualitative researcher.
                        You can answer any questions about coding logs.""",
                    },
                    {
                        "role": "user",
                        "content": f"""
## Context
The text below shows a log containing errors. Your task is to code the log with
the following codes. Generate a list of codes for the log below.

Only use the codes from the list below. Do not create new codes.
Modify the examples of the codes to fit the context of the log.

Your example should be informative to narrow down the details of the error in
the context of the example.

## Codes

{code_to_str}

## Log

{doc.text}
""",
                    },
                ],
                response_format=CodeList,
            )

            message = completion.choices[0].message
            if message.parsed and len(message.parsed.code_list) > 0:
                code_list = message.parsed.code_list
                # filter out codes whose names are not in the code_set
                code_set_names = {code.name for code in code_set}
                code_list = [code for code in code_list if code.name in code_set_names]

                coded_document = CodedDocument(doc=doc, codes=set(code_list))

        if coded_document is None:
            raise ValueError("Error in coding document with OpenAI")

        if self.cache_enabled and cache_file:
            with open(cache_file, "w") as f:
                f.write(coded_document.model_dump_json(indent=4))
        return coded_document
