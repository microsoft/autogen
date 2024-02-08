import os
import requests
import glob
from urllib.parse import urlparse
from abc import ABC, abstractmethod
from typing import List, Tuple, Union, Callable
from autogen.token_count_utils import count_token
from .datamodel import Chunk
from .utils import logger, lazy_import, timer

PLAIN_TEXT_EXTENSION = [
    ".txt",
    ".json",
    ".csv",
    ".tsv",
    ".md",
    ".html",
    ".htm",
    ".rtf",
    ".rst",
    ".jsonl",
    ".log",
    ".xml",
    ".yaml",
    ".yml",
]
PDF_EXTENSION = [".pdf"]


class Splitter(ABC):
    """
    Abstract class for splitter. A splitter is responsible for splitting raw text into chunks.
    """

    @abstractmethod
    def split(
        self,
    ) -> List[Chunk]:
        """
        Split raw text, code, metadata into chunks.

        Returns:
            List[Chunk] | The list of chunks.
        """
        raise NotImplementedError

    @staticmethod
    def get_files_from_dir(
        dir_path: Union[str, List[str]], types: list = PLAIN_TEXT_EXTENSION + PDF_EXTENSION, recursive: bool = True
    ) -> List[str]:
        """
        Get all the files in a given directory, a url, a file path or a list of them.

        Args:
            dir_path: Union[str, List[str]] | The directory path, file path, or a list of them.
            types: list | The list of file types to include. Default is PLAIN_TEXT_EXTENSION + PDF_EXTENSION.
            recursive: bool | Whether to search recursively. Default is True.

        Returns:
            List[str] | The list of file paths.
        """
        if len(types) == 0:
            raise ValueError("types cannot be empty.")
        types = [t.lower() if t.startswith(".") else "." + t.lower() for t in set(types)]
        types += [t.upper() for t in types]

        files = []
        # If the path is a list of files or urls, process and return them
        if isinstance(dir_path, list):
            for item in dir_path:
                if os.path.isfile(item):
                    files.append(item)
                elif Splitter.is_url(item):
                    files.append(Splitter.get_file_from_url(item))
                elif os.path.exists(item):
                    try:
                        files.extend(Splitter.get_files_from_dir(item, types, recursive))
                    except ValueError:
                        logger.warning(f"Directory {item} does not exist. Skipping.", color="yellow")
                else:
                    logger.warning(f"File {item} does not exist. Skipping.", color="yellow")
            return files

        # If the path is a file, return it
        if os.path.isfile(dir_path):
            return [dir_path]

        # If the path is a url, download it and return the downloaded file
        if Splitter.is_url(dir_path):
            return [Splitter.get_file_from_url(dir_path)]

        if os.path.exists(dir_path):
            for type in types:
                if recursive:
                    files += glob.glob(os.path.join(dir_path, f"**/*{type}"), recursive=True)
                else:
                    files += glob.glob(os.path.join(dir_path, f"*{type}"), recursive=False)
        else:
            logger.error(f"Directory {dir_path} does not exist.", color="red")
            raise ValueError(f"Directory {dir_path} does not exist.")
        return files

    @staticmethod
    def get_file_from_url(url: str, save_path: str = None) -> str:
        """
        Download a file from a URL.

        Args:
            url: str | The URL.
            save_path: str | The path to save the file. Default is None.

        Returns:
            str | The path to the downloaded file.
        """
        if save_path is None:
            os.makedirs("./tmp/download", exist_ok=True)
            save_path = os.path.join("./tmp/download", os.path.basename(url))
        else:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
        try:
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                with open(save_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        except requests.exceptions.HTTPError as err:
            logger.warning(f"Skipping URL due to {err.response.status_code} error: {url}", color="yellow")
            return ""
        return save_path

    @staticmethod
    def is_url(string: str) -> bool:
        """
        Check if the string is a valid URL.

        Args:
            string: str | The string to check.

        Returns:
            bool | Whether the string is a valid URL.
        """
        try:
            result = urlparse(string)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False


class TextLineSplitter(Splitter):
    """
    A simple text splitter that splits the input text into chunks based on the lines.
    """

    VALID_CHUNK_MODES = frozenset({"one_line", "multi_lines"})

    def __init__(
        self,
        docs_path: Union[str, List[str]],
        recursive: bool = True,
        chunk_size: int = 1024,  # number of tokens
        chunk_mode: str = "multi_lines",
        must_break_at_empty_line: bool = True,
        overlap: int = 1,  # number of overlapping lines
        token_count_function: Callable = count_token,
        custom_text_split_function: Callable = None,
    ) -> None:
        """
        Initialize the TextLineSplitter.

        Args:
            docs_path: Union[str, List[str]] | The directory path, file path, or a list of them.
            recursive: bool | Whether to search recursively. Default is True.
            chunk_size: int | The size of the chunk in number of tokens. Default is 1024.
            chunk_mode: str | The mode of chunking. Default is "multi_lines".
            must_break_at_empty_line: bool | Whether to break at empty lines. Default is True.
            overlap: int | The number of overlapping lines. Default is 1.
            token_count_function: Callable | The function to count the number of tokens. Default is count_token.
            custom_text_split_function: Callable | The custom text split function. Default is None.

        Returns:
            None
        """
        self.docs_path = docs_path
        self.recursive = recursive
        self.chunk_size = chunk_size
        self.chunk_mode = chunk_mode
        self.must_break_at_empty_line = must_break_at_empty_line
        self.overlap = overlap
        self.token_count_function = token_count_function
        self.custom_text_split_function = custom_text_split_function

    def split_text_to_chunks(
        self,
        text: str,
        chunk_size: int = 1024,
        chunk_mode: str = "multi_lines",
        must_break_at_empty_line: bool = True,
        overlap: int = 1,  # number of overlapping lines
    ) -> List[str]:
        """
        Split a long text into chunks of chunk_size.

        Args:
            text: str | The input text.
            chunk_size: int | The size of the chunk in number of tokens. Default is 1024.
            chunk_mode: str | The mode of chunking. Default is "multi_lines".
            must_break_at_empty_line: bool | Whether to break at empty lines. Default is True.
            overlap: int | The number of overlapping lines. Default is 1.

        Returns:
            List[str] | The list of chunks.
        """
        if chunk_mode not in self.VALID_CHUNK_MODES:
            raise AssertionError
        if chunk_mode == "one_line":
            must_break_at_empty_line = False
            overlap = 0
        chunks = []
        lines = text.split("\n")
        lines_tokens = [count_token(line) for line in lines]
        sum_tokens = sum(lines_tokens)
        while sum_tokens > chunk_size:
            if chunk_mode == "one_line":
                estimated_line_cut = 2
            else:
                estimated_line_cut = int(chunk_size / sum_tokens * len(lines)) + 1
            cnt = 0
            prev = ""
            for cnt in reversed(range(estimated_line_cut)):
                if must_break_at_empty_line and lines[cnt].strip() != "":
                    continue
                if sum(lines_tokens[:cnt]) <= chunk_size:
                    prev = "\n".join(lines[:cnt])
                    break
            if cnt == 0:
                logger.warning(
                    f"chunk_size is too small to fit a single line of text. Breaking this line:\n\t{lines[0][:100]} ...",
                    color="yellow",
                )
                if not must_break_at_empty_line:
                    split_len = int(chunk_size / (lines_tokens[0] * 0.9 * len(lines[0]) + 0.1))
                    prev = lines[0][:split_len]
                    lines[0] = lines[0][split_len:]
                    lines_tokens[0] = count_token(lines[0])
                else:
                    logger.warning(
                        "Failed to split docs with must_break_at_empty_line being True, set to False.", color="yellow"
                    )
                    must_break_at_empty_line = False
            chunks.append(prev) if len(prev) > 10 else None  # don't add chunks less than 10 characters
            lines = lines[cnt - overlap if cnt > overlap else cnt :]
            lines_tokens = lines_tokens[cnt - overlap if cnt > overlap else cnt :]
            sum_tokens = sum(lines_tokens)
        text_to_chunk = "\n".join(lines).strip()
        chunks.append(text_to_chunk) if len(text_to_chunk) > 10 else None  # don't add chunks less than 10 characters
        return chunks

    @staticmethod
    def extract_text_from_pdf(file: str) -> str:
        """
        Extract text from PDF files

        Args:
            file: str | The file path.

        Returns:
            str | The extracted text.
        """
        text = ""
        pypdf = lazy_import("pypdf")
        with open(file, "rb") as f:
            reader = pypdf.PdfReader(f)
            if reader.is_encrypted:  # Check if the PDF is encrypted
                try:
                    reader.decrypt("")
                except pypdf.errors.FileNotDecryptedError as e:
                    logger.warning(f"Could not decrypt PDF {file}, {e}", color="yellow")
                    return text  # Return empty text if PDF could not be decrypted

            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text += page.extract_text()

        if not text.strip():  # Debugging line to check if text is empty
            logger.warning(f"Could not decrypt PDF {file}", color="yellow")

        return text

    def split_files_to_chunks(
        self,
        files: list,
        chunk_size: int = 1024,
        chunk_mode: str = "multi_lines",
        must_break_at_empty_line: bool = True,
        overlap: int = 1,  # number of overlapping lines
        custom_text_split_function: Callable = None,
    ) -> Tuple[List, List]:
        """
        Split a list of files into chunks of chunk_size.

        Args:
            files: list | The list of files.
            chunk_size: int | The size of the chunk in number of tokens. Default is 1024.
            chunk_mode: str | The mode of chunking. Default is "multi_lines".
            must_break_at_empty_line: bool | Whether to break at empty lines. Default is True.
            overlap: int | The number of overlapping lines. Default is 1.
            custom_text_split_function: Callable | The custom text split function. Default is None.

        Returns:
            Tuple[List, List] | The list of chunks and the list of sources.
        """
        chunks = []
        sources = []

        for file in files:
            logger.debug(f"Processing file: {file}")
            _, file_extension = os.path.splitext(file)
            file_extension = file_extension.lower()

            if file_extension == ".pdf":
                text = self.extract_text_from_pdf(file)
            else:  # For non-PDF text-based files
                with open(file, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()

            if not text.strip():  # Debugging line to check if text is empty after reading
                logger.warning(f"No text available in file: {file}", color="yellow")
                continue  # Skip to the next file if no text is available

            if custom_text_split_function is not None:
                tmp_chunks = custom_text_split_function(text)
            else:
                tmp_chunks = self.split_text_to_chunks(text, chunk_size, chunk_mode, must_break_at_empty_line, overlap)
            chunks += tmp_chunks
            sources += [file] * len(tmp_chunks)
            logger.debug(f"Split {file} into {len(tmp_chunks)} chunks.", color="green")
        return chunks, sources

    @timer
    def split(
        self,
    ) -> List[Chunk]:
        """
        Split raw text, code, metadata into chunks.

        Returns:
            List[Chunk] | The list of chunks.
        """
        self.files = Splitter.get_files_from_dir(self.docs_path, recursive=self.recursive)
        chunks, sources = self.split_files_to_chunks(
            self.files,
            self.chunk_size,
            self.chunk_mode,
            self.must_break_at_empty_line,
            self.overlap,
            self.custom_text_split_function,
        )
        return [Chunk(content=chunk, metadata={"source": source}) for chunk, source in zip(chunks, sources)]


class SplitterFactory:
    """
    Factory class for creating splitters.
    """

    PREDEFINED_SPLITTERS = frozenset({"textline"})

    @staticmethod
    def create_splitter(
        splitter: str,
        docs_path: Union[str, List[str]],
        recursive: bool = True,
        chunk_size: int = 1024,  # number of tokens
        chunk_mode: str = "multi_lines",
        must_break_at_empty_line: bool = True,
        overlap: int = 1,  # number of overlapping lines
        token_count_function: Callable = count_token,
        custom_text_split_function: Callable = None,
    ) -> Splitter:
        """
        Create a splitter.

        Args:
            splitter: str | The name of the splitter.
            docs_path: Union[str, List[str]] | The directory path, file path, or a list of them.
            recursive: bool | Whether to search recursively. Default is True.
            chunk_size: int | The size of the chunk in number of tokens. Default is 1024.
            chunk_mode: str | The mode of chunking. Default is "multi_lines".
            must_break_at_empty_line: bool | Whether to break at empty lines. Default is True.
            overlap: int | The number of overlapping lines. Default is 1.
            token_count_function: Callable | The function to count the number of tokens. Default is count_token.
            custom_text_split_function: Callable | The custom text split function. Default is None.

        Returns:
            Splitter | The splitter.
        """
        if splitter == "textline":
            return TextLineSplitter(
                docs_path,
                recursive,
                chunk_size,
                chunk_mode,
                must_break_at_empty_line,
                overlap,
                token_count_function,
                custom_text_split_function,
            )
        else:
            raise ValueError(
                f"Invalid splitter: {splitter}. Valid splitters are {SplitterFactory.PREDEFINED_SPLITTERS}"
            )
