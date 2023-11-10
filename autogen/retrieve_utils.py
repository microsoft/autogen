from typing import List, Union, Callable
import os
import requests
from urllib.parse import urlparse
import glob
import logging
import pypdf
from autogen.token_count_utils import count_token

try:
    from unstructured.partition.auto import partition

    HAS_UNSTRUCTURED = True
except ImportError:
    HAS_UNSTRUCTURED = False

logger = logging.getLogger(__name__)
TEXT_FORMATS = [
    "txt",
    "json",
    "csv",
    "tsv",
    "md",
    "html",
    "htm",
    "rtf",
    "rst",
    "jsonl",
    "log",
    "xml",
    "yaml",
    "yml",
    "pdf",
]
UNSTRUCTURED_FORMATS = ["docx", "doc", "odt", "pptx", "ppt", "xlsx", "eml", "msg", "epub"]
if HAS_UNSTRUCTURED:
    TEXT_FORMATS += UNSTRUCTURED_FORMATS
    TEXT_FORMATS = list(set(TEXT_FORMATS))
VALID_CHUNK_MODES = frozenset({"one_line", "multi_lines"})


def split_text_to_chunks(
    text: str,
    max_tokens: int = 4000,
    chunk_mode: str = "multi_lines",
    must_break_at_empty_line: bool = True,
    overlap: int = 10,
):
    """Split a long text into chunks of max_tokens."""
    if chunk_mode not in VALID_CHUNK_MODES:
        raise AssertionError
    if chunk_mode == "one_line":
        must_break_at_empty_line = False
    chunks = []
    lines = text.split("\n")
    lines_tokens = [count_token(line) for line in lines]
    sum_tokens = sum(lines_tokens)
    while sum_tokens > max_tokens:
        if chunk_mode == "one_line":
            estimated_line_cut = 2
        else:
            estimated_line_cut = int(max_tokens / sum_tokens * len(lines)) + 1
        cnt = 0
        prev = ""
        for cnt in reversed(range(estimated_line_cut)):
            if must_break_at_empty_line and lines[cnt].strip() != "":
                continue
            if sum(lines_tokens[:cnt]) <= max_tokens:
                prev = "\n".join(lines[:cnt])
                break
        if cnt == 0:
            logger.warning(
                f"max_tokens is too small to fit a single line of text. Breaking this line:\n\t{lines[0][:100]} ..."
            )
            if not must_break_at_empty_line:
                split_len = int(max_tokens / lines_tokens[0] * 0.9 * len(lines[0]))
                prev = lines[0][:split_len]
                lines[0] = lines[0][split_len:]
                lines_tokens[0] = count_token(lines[0])
            else:
                logger.warning("Failed to split docs with must_break_at_empty_line being True, set to False.")
                must_break_at_empty_line = False
        chunks.append(prev) if len(prev) > 10 else None  # don't add chunks less than 10 characters
        lines = lines[cnt:]
        lines_tokens = lines_tokens[cnt:]
        sum_tokens = sum(lines_tokens)
    text_to_chunk = "\n".join(lines)
    chunks.append(text_to_chunk) if len(text_to_chunk) > 10 else None  # don't add chunks less than 10 characters
    return chunks


def extract_text_from_pdf(file: str) -> str:
    """Extract text from PDF files"""
    text = ""
    with open(file, "rb") as f:
        reader = pypdf.PdfReader(f)
        if reader.is_encrypted:  # Check if the PDF is encrypted
            try:
                reader.decrypt("")
            except pypdf.errors.FileNotDecryptedError as e:
                logger.warning(f"Could not decrypt PDF {file}, {e}")
                return text  # Return empty text if PDF could not be decrypted

        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            text += page.extract_text()

    if not text.strip():  # Debugging line to check if text is empty
        logger.warning(f"Could not decrypt PDF {file}")

    return text


def split_files_to_chunks(
    files: list,
    max_tokens: int = 4000,
    chunk_mode: str = "multi_lines",
    must_break_at_empty_line: bool = True,
    custom_text_split_function: Callable = None,
):
    """Split a list of files into chunks of max_tokens."""

    chunks = []

    for file in files:
        _, file_extension = os.path.splitext(file)
        file_extension = file_extension.lower()

        if HAS_UNSTRUCTURED and file_extension[1:] in UNSTRUCTURED_FORMATS:
            text = partition(file)
            text = "\n".join([t.text for t in text]) if len(text) > 0 else ""
        elif file_extension == ".pdf":
            text = extract_text_from_pdf(file)
        else:  # For non-PDF text-based files
            with open(file, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()

        if not text.strip():  # Debugging line to check if text is empty after reading
            logger.warning(f"No text available in file: {file}")
            continue  # Skip to the next file if no text is available

        if custom_text_split_function is not None:
            chunks += custom_text_split_function(text)
        else:
            chunks += split_text_to_chunks(text, max_tokens, chunk_mode, must_break_at_empty_line)

    return chunks


def get_files_from_dir(dir_path: Union[str, List[str]], types: list = TEXT_FORMATS, recursive: bool = True):
    """Return a list of all the files in a given directory."""
    if len(types) == 0:
        raise ValueError("types cannot be empty.")
    types = [t[1:].lower() if t.startswith(".") else t.lower() for t in set(types)]
    types += [t.upper() for t in types]

    files = []
    # If the path is a list of files or urls, process and return them
    if isinstance(dir_path, list):
        for item in dir_path:
            if os.path.isfile(item):
                files.append(item)
            elif is_url(item):
                files.append(get_file_from_url(item))
            else:
                logger.warning(f"File {item} does not exist. Skipping.")
        return files

    # If the path is a file, return it
    if os.path.isfile(dir_path):
        return [dir_path]

    # If the path is a url, download it and return the downloaded file
    if is_url(dir_path):
        return [get_file_from_url(dir_path)]

    if os.path.exists(dir_path):
        for type in types:
            if recursive:
                files += glob.glob(os.path.join(dir_path, f"**/*.{type}"), recursive=True)
            else:
                files += glob.glob(os.path.join(dir_path, f"*.{type}"), recursive=False)
    else:
        logger.error(f"Directory {dir_path} does not exist.")
        raise ValueError(f"Directory {dir_path} does not exist.")
    return files


def get_file_from_url(url: str, save_path: str = None):
    """Download a file from a URL."""
    if save_path is None:
        os.makedirs("/tmp/chromadb", exist_ok=True)
        save_path = os.path.join("/tmp/chromadb", os.path.basename(url))
    else:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return save_path


def is_url(string: str):
    """Return True if the string is a valid URL."""
    try:
        result = urlparse(string)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False
