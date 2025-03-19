import os
import argparse
from typing import List, Sequence, Optional
from ._base import Document, CodedDocument
from .coders.oai_coder import OAIQualitativeCoder


def prepend_line_numbers(lines: List[str]) -> List[str]:
    """
    Returns a list of strings with each line prefixed by its right-justified
      line number.
    """
    width = len(str(len(lines)))
    new_lines = [f"{i+1:>{width}}: {line}" for i, line in enumerate(lines)]
    return new_lines


def load_log_file(path: str, prepend_numbers: bool = False) -> Document:
    with open(path, "r") as f:
        lines = f.readlines()
    if prepend_numbers:
        lines = prepend_line_numbers(lines)

    text = "".join(lines)
    return Document(text=text, name=os.path.abspath(path))


def code_log(path: str) -> Optional[CodedDocument]:
    coder = OAIQualitativeCoder()

    if os.path.isfile(path):
        doc = load_log_file(path, prepend_numbers=True)
        coded_doc = coder.code_document(doc)
        return coded_doc
    else:
        raise FileNotFoundError(f"File {path} does not exist.")


def print_coded_results(input_path: str, coded_doc: CodedDocument) -> None:
    num_errors: int = 0
    
    for code in coded_doc.codes:
        print(f"\033[31mCategory: {code.name}\033[0m: {code.definition}")
        for example in code.examples:
            print(
                f"\033[1m{input_path}\033[0m:{example.line}"
                f":{example.line_end}\t{example.reason}"
            )
            num_errors += 1
    print("\n")
    print(f"Found {num_errors} errors in {input_path}.")
    print("\n")


def code_command(input_path: str) -> None:
    """
    Process the given input path by coding log files.
    """
    if os.path.isfile(input_path):
        coded_doc = code_log(input_path)
        if coded_doc is None:
            raise ValueError("Failed to code the document.")
        print_coded_results(input_path, coded_doc)
    else:
        print("Invalid input path.")


def lint_cli(args: Sequence[str]) -> None:
    
    invocation_cmd = args[0]
    
    args = args[1:]
    
    parser = argparse.ArgumentParser(
        prog=invocation_cmd,
        description=f"{invocation_cmd} will analyze a console log."
        " And detect errors/inefficiencies in the log files."
    )

    parser.add_argument("logfile",
                        type=str,
                        help="Path to a log file.")

    parsed_args = parser.parse_args(args)
    
    code_command(parsed_args.logfile)
