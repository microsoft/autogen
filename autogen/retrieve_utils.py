from typing import List, Union, Dict, Tuple, Callable
import os
import requests
from urllib.parse import urlparse
import glob
import tiktoken
import chromadb

if chromadb.__version__ < "0.4.15":
    from chromadb.api import API
else:
    from chromadb.api import ClientAPI as API
from chromadb.api.types import QueryResult
import chromadb.utils.embedding_functions as ef
import logging
import pypdf


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
VALID_CHUNK_MODES = frozenset({"one_line", "multi_lines"})


def num_tokens_from_text(
    text: str,
    model: str = "gpt-3.5-turbo-0613",
    return_tokens_per_name_and_message: bool = False,
    custom_token_count_function: Callable = None,
) -> Union[int, Tuple[int, int, int]]:
    """Return the number of tokens used by a text.

    Args:
        text (str): The text to count tokens for.
        model (Optional, str): The model to use for tokenization. Default is "gpt-3.5-turbo-0613".
        return_tokens_per_name_and_message (Optional, bool): Whether to return the number of tokens per name and per
            message. Default is False.
        custom_token_count_function (Optional, Callable): A custom function to count tokens. Default is None.

    Returns:
        int: The number of tokens used by the text.
        int: The number of tokens per message. Only returned if return_tokens_per_name_and_message is True.
        int: The number of tokens per name. Only returned if return_tokens_per_name_and_message is True.
    """
    if isinstance(custom_token_count_function, Callable):
        token_count, tokens_per_message, tokens_per_name = custom_token_count_function(text)
    else:
        # https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            logger.debug("Warning: model not found. Using cl100k_base encoding.")
            encoding = tiktoken.get_encoding("cl100k_base")
        known_models = {
            "gpt-3.5-turbo": (3, 1),
            "gpt-35-turbo": (3, 1),
            "gpt-3.5-turbo-0613": (3, 1),
            "gpt-3.5-turbo-16k-0613": (3, 1),
            "gpt-3.5-turbo-0301": (4, -1),
            "gpt-4": (3, 1),
            "gpt-4-0314": (3, 1),
            "gpt-4-32k-0314": (3, 1),
            "gpt-4-0613": (3, 1),
            "gpt-4-32k-0613": (3, 1),
        }
        tokens_per_message, tokens_per_name = known_models.get(model, (3, 1))
        token_count = len(encoding.encode(text))

    if return_tokens_per_name_and_message:
        return token_count, tokens_per_message, tokens_per_name
    else:
        return token_count


def num_tokens_from_messages(
    messages: dict,
    model: str = "gpt-3.5-turbo-0613",
    custom_token_count_function: Callable = None,
    custom_prime_count: int = 3,
):
    """Return the number of tokens used by a list of messages."""
    num_tokens = 0
    for message in messages:
        for key, value in message.items():
            _num_tokens, tokens_per_message, tokens_per_name = num_tokens_from_text(
                value,
                model=model,
                return_tokens_per_name_and_message=True,
                custom_token_count_function=custom_token_count_function,
            )
            num_tokens += _num_tokens
            if key == "name":
                num_tokens += tokens_per_name
        num_tokens += tokens_per_message
    num_tokens += custom_prime_count  # With ChatGPT, every reply is primed with <|start|>assistant<|message|>
    return num_tokens


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
    lines_tokens = [num_tokens_from_text(line) for line in lines]
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
                lines_tokens[0] = num_tokens_from_text(lines[0])
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

        if file_extension == ".pdf":
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


def create_vector_db_from_dir(
    dir_path: str,
    max_tokens: int = 4000,
    client: API = None,
    db_path: str = "/tmp/chromadb.db",
    collection_name: str = "all-my-documents",
    get_or_create: bool = False,
    chunk_mode: str = "multi_lines",
    must_break_at_empty_line: bool = True,
    embedding_model: str = "all-MiniLM-L6-v2",
    embedding_function: Callable = None,
    custom_text_split_function: Callable = None,
) -> API:
    """Create a vector db from all the files in a given directory, the directory can also be a single file or a url to
        a single file. We support chromadb compatible APIs to create the vector db, this function is not required if
        you prepared your own vector db.

    Args:
        dir_path (str): the path to the directory, file or url.
        max_tokens (Optional, int): the maximum number of tokens per chunk. Default is 4000.
        client (Optional, API): the chromadb client. Default is None.
        db_path (Optional, str): the path to the chromadb. Default is "/tmp/chromadb.db".
        collection_name (Optional, str): the name of the collection. Default is "all-my-documents".
        get_or_create (Optional, bool): Whether to get or create the collection. Default is False. If True, the collection
            will be recreated if it already exists.
        chunk_mode (Optional, str): the chunk mode. Default is "multi_lines".
        must_break_at_empty_line (Optional, bool): Whether to break at empty line. Default is True.
        embedding_model (Optional, str): the embedding model to use. Default is "all-MiniLM-L6-v2". Will be ignored if
            embedding_function is not None.
        embedding_function (Optional, Callable): the embedding function to use. Default is None, SentenceTransformer with
            the given `embedding_model` will be used. If you want to use OpenAI, Cohere, HuggingFace or other embedding
            functions, you can pass it here, follow the examples in `https://docs.trychroma.com/embeddings`.

    Returns:
        API: the chromadb client.
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

        if custom_text_split_function is not None:
            chunks = split_files_to_chunks(
                get_files_from_dir(dir_path), custom_text_split_function=custom_text_split_function
            )
        else:
            chunks = split_files_to_chunks(
                get_files_from_dir(dir_path), max_tokens, chunk_mode, must_break_at_empty_line
            )
        logger.info(f"Found {len(chunks)} chunks.")
        # Upsert in batch of 40000 or less if the total number of chunks is less than 40000
        for i in range(0, len(chunks), min(40000, len(chunks))):
            end_idx = i + min(40000, len(chunks) - i)
            collection.upsert(
                documents=chunks[i:end_idx],
                ids=[f"doc_{j}" for j in range(i, end_idx)],  # unique for each doc
            )
    except ValueError as e:
        logger.warning(f"{e}")
    return client


def query_vector_db(
    query_texts: List[str],
    n_results: int = 10,
    client: API = None,
    db_path: str = "/tmp/chromadb.db",
    collection_name: str = "all-my-documents",
    search_string: str = "",
    embedding_model: str = "all-MiniLM-L6-v2",
    embedding_function: Callable = None,
) -> QueryResult:
    """Query a vector db. We support chromadb compatible APIs, it's not required if you prepared your own vector db
        and query function.

    Args:
        query_texts (List[str]): the query texts.
        n_results (Optional, int): the number of results to return. Default is 10.
        client (Optional, API): the chromadb compatible client. Default is None, a chromadb client will be used.
        db_path (Optional, str): the path to the vector db. Default is "/tmp/chromadb.db".
        collection_name (Optional, str): the name of the collection. Default is "all-my-documents".
        search_string (Optional, str): the search string. Default is "".
        embedding_model (Optional, str): the embedding model to use. Default is "all-MiniLM-L6-v2". Will be ignored if
            embedding_function is not None.
        embedding_function (Optional, Callable): the embedding function to use. Default is None, SentenceTransformer with
            the given `embedding_model` will be used. If you want to use OpenAI, Cohere, HuggingFace or other embedding
            functions, you can pass it here, follow the examples in `https://docs.trychroma.com/embeddings`.

    Returns:
        QueryResult: the query result. The format is:
            class QueryResult(TypedDict):
                ids: List[IDs]
                embeddings: Optional[List[List[Embedding]]]
                documents: Optional[List[List[Document]]]
                metadatas: Optional[List[List[Metadata]]]
                distances: Optional[List[List[float]]]
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
