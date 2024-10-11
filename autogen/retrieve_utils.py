import glob
import hashlib
import os
import re
from typing import Callable, List, Tuple, Union
from urllib.parse import urlparse

import chromadb
import markdownify
import requests
from bs4 import BeautifulSoup

if chromadb.__version__ < "0.4.15":
    from chromadb.api import API
else:
    from chromadb.api import ClientAPI as API
import logging

import chromadb.utils.embedding_functions as ef
import pypdf
from chromadb.api.types import QueryResult

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
UNSTRUCTURED_FORMATS = [
    "doc",
    "docx",
    "epub",
    "msg",
    "odt",
    "org",
    "pdf",
    "ppt",
    "pptx",
    "rtf",
    "rst",
    "xlsx",
]  # These formats will be parsed by the 'unstructured' library, if installed.
if HAS_UNSTRUCTURED:
    TEXT_FORMATS += UNSTRUCTURED_FORMATS
    TEXT_FORMATS = list(set(TEXT_FORMATS))
VALID_CHUNK_MODES = frozenset({"one_line", "multi_lines"})
RAG_MINIMUM_MESSAGE_LENGTH = int(os.environ.get("RAG_MINIMUM_MESSAGE_LENGTH", 5))


def split_text_to_chunks(
    text: str,
    max_tokens: int = 4000,
    chunk_mode: str = "multi_lines",
    must_break_at_empty_line: bool = True,
    overlap: int = 0,  # number of overlapping lines
):
    """Split a long text into chunks of max_tokens."""
    if chunk_mode not in VALID_CHUNK_MODES:
        raise AssertionError
    if chunk_mode == "one_line":
        must_break_at_empty_line = False
        overlap = 0
    chunks = []
    lines = text.split("\n")
    num_lines = len(lines)
    if num_lines < 3 and must_break_at_empty_line:
        logger.warning("The input text has less than 3 lines. Set `must_break_at_empty_line` to `False`")
        must_break_at_empty_line = False
    lines_tokens = [count_token(line) for line in lines]
    sum_tokens = sum(lines_tokens)
    while sum_tokens > max_tokens:
        if chunk_mode == "one_line":
            estimated_line_cut = 2
        else:
            estimated_line_cut = max(int(max_tokens / sum_tokens * len(lines)), 2)
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
                split_len = max(
                    int(max_tokens / (lines_tokens[0] * 0.9 * len(lines[0]) + 0.1)), RAG_MINIMUM_MESSAGE_LENGTH
                )
                prev = lines[0][:split_len]
                lines[0] = lines[0][split_len:]
                lines_tokens[0] = count_token(lines[0])
            else:
                logger.warning("Failed to split docs with must_break_at_empty_line being True, set to False.")
                must_break_at_empty_line = False
        (
            chunks.append(prev) if len(prev) >= RAG_MINIMUM_MESSAGE_LENGTH else None
        )  # don't add chunks less than RAG_MINIMUM_MESSAGE_LENGTH characters
        lines = lines[cnt - overlap if cnt > overlap else cnt :]
        lines_tokens = lines_tokens[cnt - overlap if cnt > overlap else cnt :]
        sum_tokens = sum(lines_tokens)
    text_to_chunk = "\n".join(lines).strip()
    (
        chunks.append(text_to_chunk) if len(text_to_chunk) >= RAG_MINIMUM_MESSAGE_LENGTH else None
    )  # don't add chunks less than RAG_MINIMUM_MESSAGE_LENGTH characters
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
) -> Tuple[List[str], List[dict]]:
    """Split a list of files into chunks of max_tokens."""

    chunks = []
    sources = []

    for file in files:
        if isinstance(file, tuple):
            url = file[1]
            file = file[0]
        else:
            url = None
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
            tmp_chunks = custom_text_split_function(text)
        else:
            tmp_chunks = split_text_to_chunks(text, max_tokens, chunk_mode, must_break_at_empty_line)
        chunks += tmp_chunks
        sources += [{"source": url if url else file}] * len(tmp_chunks)

    return chunks, sources


def get_files_from_dir(dir_path: Union[str, List[str]], types: list = TEXT_FORMATS, recursive: bool = True):
    """Return a list of all the files in a given directory, a url, a file path or a list of them."""
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
                filepath = get_file_from_url(item)
                if filepath:
                    files.append(filepath)
            elif os.path.exists(item):
                try:
                    files.extend(get_files_from_dir(item, types, recursive))
                except ValueError:
                    logger.warning(f"Directory {item} does not exist. Skipping.")
            else:
                logger.warning(f"File {item} does not exist. Skipping.")
        return files

    # If the path is a file, return it
    if os.path.isfile(dir_path):
        return [dir_path]

    # If the path is a url, download it and return the downloaded file
    if is_url(dir_path):
        filepath = get_file_from_url(dir_path)
        if filepath:
            return [filepath]
        else:
            return []

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


def parse_html_to_markdown(html: str, url: str = None) -> str:
    """Parse HTML to markdown."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string
    # Remove javascript and style blocks
    for script in soup(["script", "style"]):
        script.extract()

    # Convert to markdown -- Wikipedia gets special attention to get a clean version of the page
    if isinstance(url, str) and url.startswith("https://en.wikipedia.org/"):
        body_elm = soup.find("div", {"id": "mw-content-text"})
        title_elm = soup.find("span", {"class": "mw-page-title-main"})

        if body_elm:
            # What's the title
            main_title = soup.title.string
            if title_elm and len(title_elm) > 0:
                main_title = title_elm.string
            webpage_text = "# " + main_title + "\n\n" + markdownify.MarkdownConverter().convert_soup(body_elm)
        else:
            webpage_text = markdownify.MarkdownConverter().convert_soup(soup)
    else:
        webpage_text = markdownify.MarkdownConverter().convert_soup(soup)

    # Convert newlines
    webpage_text = re.sub(r"\r\n", "\n", webpage_text)
    webpage_text = re.sub(r"\n{2,}", "\n\n", webpage_text).strip()
    webpage_text = "# " + title + "\n\n" + webpage_text
    return webpage_text


def _generate_file_name_from_url(url: str, max_length=255) -> str:
    url_bytes = url.encode("utf-8")
    hash = hashlib.blake2b(url_bytes).hexdigest()
    parsed_url = urlparse(url)
    file_name = os.path.basename(url)
    file_name = f"{parsed_url.netloc}_{file_name}_{hash[:min(8, max_length-len(parsed_url.netloc)-len(file_name)-1)]}"
    return file_name


def get_file_from_url(url: str, save_path: str = None) -> Tuple[str, str]:
    """Download a file from a URL."""
    if save_path is None:
        save_path = "tmp/chromadb"
        os.makedirs(save_path, exist_ok=True)
    if os.path.isdir(save_path):
        filename = _generate_file_name_from_url(url)
        save_path = os.path.join(save_path, filename)
    else:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

    custom_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    }
    try:
        response = requests.get(url, stream=True, headers=custom_headers, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to download {url}, {e}")
        return None

    content_type = response.headers.get("content-type", "")
    if "text/html" in content_type:
        # Get the content of the response
        html = ""
        for chunk in response.iter_content(chunk_size=8192, decode_unicode=True):
            html += chunk
        text = parse_html_to_markdown(html, url)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        with open(save_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    return save_path, url


def is_url(string: str):
    """Return True if the string is a valid URL."""
    try:
        result = urlparse(string)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def create_vector_db_from_dir(
    dir_path: Union[str, List[str]],
    max_tokens: int = 4000,
    client: API = None,
    db_path: str = "tmp/chromadb.db",
    collection_name: str = "all-my-documents",
    get_or_create: bool = False,
    chunk_mode: str = "multi_lines",
    must_break_at_empty_line: bool = True,
    embedding_model: str = "all-MiniLM-L6-v2",
    embedding_function: Callable = None,
    custom_text_split_function: Callable = None,
    custom_text_types: List[str] = TEXT_FORMATS,
    recursive: bool = True,
    extra_docs: bool = False,
) -> API:
    """Create a vector db from all the files in a given directory, the directory can also be a single file or a url to
        a single file. We support chromadb compatible APIs to create the vector db, this function is not required if
        you prepared your own vector db.

    Args:
        dir_path (Union[str, List[str]]): the path to the directory, file, url or a list of them.
        max_tokens (Optional, int): the maximum number of tokens per chunk. Default is 4000.
        client (Optional, API): the chromadb client. Default is None.
        db_path (Optional, str): the path to the chromadb. Default is "tmp/chromadb.db". The default was `/tmp/chromadb.db` for version <=0.2.24.
        collection_name (Optional, str): the name of the collection. Default is "all-my-documents".
        get_or_create (Optional, bool): Whether to get or create the collection. Default is False. If True, the collection
            will be returned if it already exists. Will raise ValueError if the collection already exists and get_or_create is False.
        chunk_mode (Optional, str): the chunk mode. Default is "multi_lines".
        must_break_at_empty_line (Optional, bool): Whether to break at empty line. Default is True.
        embedding_model (Optional, str): the embedding model to use. Default is "all-MiniLM-L6-v2". Will be ignored if
            embedding_function is not None.
        embedding_function (Optional, Callable): the embedding function to use. Default is None, SentenceTransformer with
            the given `embedding_model` will be used. If you want to use OpenAI, Cohere, HuggingFace or other embedding
            functions, you can pass it here, follow the examples in `https://docs.trychroma.com/guides/embeddings`.
        custom_text_split_function (Optional, Callable): a custom function to split a string into a list of strings.
            Default is None, will use the default function in `autogen.retrieve_utils.split_text_to_chunks`.
        custom_text_types (Optional, List[str]): a list of file types to be processed. Default is TEXT_FORMATS.
        recursive (Optional, bool): whether to search documents recursively in the dir_path. Default is True.
        extra_docs (Optional, bool): whether to add more documents in the collection. Default is False

    Returns:

    The chromadb client.
    """
    if client is None:
        client = chromadb.PersistentClient(path=db_path)
    try:
        embedding_function = (
            ef.SentenceTransformerEmbeddingFunction(embedding_model)
            if embedding_function is None
            else embedding_function
        )
        collection = client.create_collection(
            collection_name,
            get_or_create=get_or_create,
            embedding_function=embedding_function,
            # https://github.com/nmslib/hnswlib#supported-distances
            # https://github.com/chroma-core/chroma/blob/566bc80f6c8ee29f7d99b6322654f32183c368c4/chromadb/segment/impl/vector/local_hnsw.py#L184
            # https://github.com/nmslib/hnswlib/blob/master/ALGO_PARAMS.md
            metadata={"hnsw:space": "ip", "hnsw:construction_ef": 30, "hnsw:M": 32},  # ip, l2, cosine
        )

        length = 0
        if extra_docs:
            length = len(collection.get()["ids"])

        if custom_text_split_function is not None:
            chunks, sources = split_files_to_chunks(
                get_files_from_dir(dir_path, custom_text_types, recursive),
                custom_text_split_function=custom_text_split_function,
            )
        else:
            chunks, sources = split_files_to_chunks(
                get_files_from_dir(dir_path, custom_text_types, recursive),
                max_tokens,
                chunk_mode,
                must_break_at_empty_line,
            )
        logger.info(f"Found {len(chunks)} chunks.")
        # Upsert in batch of 40000 or less if the total number of chunks is less than 40000
        for i in range(0, len(chunks), min(40000, len(chunks))):
            end_idx = i + min(40000, len(chunks) - i)
            collection.upsert(
                documents=chunks[i:end_idx],
                ids=[f"doc_{j+length}" for j in range(i, end_idx)],  # unique for each doc
                metadatas=sources[i:end_idx],
            )
    except ValueError as e:
        logger.warning(f"{e}")
    return client


def query_vector_db(
    query_texts: List[str],
    n_results: int = 10,
    client: API = None,
    db_path: str = "tmp/chromadb.db",
    collection_name: str = "all-my-documents",
    search_string: str = "",
    embedding_model: str = "all-MiniLM-L6-v2",
    embedding_function: Callable = None,
) -> QueryResult:
    """Query a vector db. We support chromadb compatible APIs, it's not required if you prepared your own vector db
        and query function.

    Args:
        query_texts (List[str]): the list of strings which will be used to query the vector db.
        n_results (Optional, int): the number of results to return. Default is 10.
        client (Optional, API): the chromadb compatible client. Default is None, a chromadb client will be used.
        db_path (Optional, str): the path to the vector db. Default is "tmp/chromadb.db". The default was `/tmp/chromadb.db` for version <=0.2.24.
        collection_name (Optional, str): the name of the collection. Default is "all-my-documents".
        search_string (Optional, str): the search string. Only docs that contain an exact match of this string will be retrieved. Default is "".
        embedding_model (Optional, str): the embedding model to use. Default is "all-MiniLM-L6-v2". Will be ignored if
            embedding_function is not None.
        embedding_function (Optional, Callable): the embedding function to use. Default is None, SentenceTransformer with
            the given `embedding_model` will be used. If you want to use OpenAI, Cohere, HuggingFace or other embedding
            functions, you can pass it here, follow the examples in `https://docs.trychroma.com/guides/embeddings`.

    Returns:

        The query result. The format is:

    ```python
    class QueryResult(TypedDict):
        ids: List[IDs]
        embeddings: Optional[List[List[Embedding]]]
        documents: Optional[List[List[Document]]]
        metadatas: Optional[List[List[Metadata]]]
        distances: Optional[List[List[float]]]
    ```
    """
    if client is None:
        client = chromadb.PersistentClient(path=db_path)
    # the collection's embedding function is always the default one, but we want to use the one we used to create the
    # collection. So we compute the embeddings ourselves and pass it to the query function.
    collection = client.get_collection(collection_name)
    embedding_function = (
        ef.SentenceTransformerEmbeddingFunction(embedding_model) if embedding_function is None else embedding_function
    )
    query_embeddings = embedding_function(query_texts)
    # Query/search n most similar results. You can also .get by id
    results = collection.query(
        query_embeddings=query_embeddings,
        n_results=n_results,
        where_document={"$contains": search_string} if search_string else None,  # optional filter
    )
    return results
