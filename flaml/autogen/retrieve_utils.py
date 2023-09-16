from typing import List, Union, Dict, Tuple
import os
import requests
from urllib.parse import urlparse
import glob
import tiktoken
import chromadb
from chromadb.api import API
import chromadb.utils.embedding_functions as ef
import logging

logger = logging.getLogger(__name__)
TEXT_FORMATS = ["txt", "json", "csv", "tsv", "md", "html", "htm", "rtf", "rst", "jsonl", "log", "xml", "yaml", "yml"]


def num_tokens_from_text(
    text: str, model: str = "gpt-3.5-turbo-0613", return_tokens_per_name_and_message: bool = False
) -> Union[int, Tuple[int, int, int]]:
    """Return the number of tokens used by a text."""
    # https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        logger.debug("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model in {
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-16k-0613",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
    }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif "gpt-3.5-turbo" in model or "gpt-35-turbo" in model:
        print("Warning: gpt-3.5-turbo may update over time. Returning num tokens assuming gpt-3.5-turbo-0613.")
        return num_tokens_from_text(text, model="gpt-3.5-turbo-0613")
    elif "gpt-4" in model:
        print("Warning: gpt-4 may update over time. Returning num tokens assuming gpt-4-0613.")
        return num_tokens_from_text(text, model="gpt-4-0613")
    else:
        raise NotImplementedError(
            f"""num_tokens_from_text() is not implemented for model {model}. See """
            f"""https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are """
            f"""converted to tokens."""
        )
    if return_tokens_per_name_and_message:
        return len(encoding.encode(text)), tokens_per_message, tokens_per_name
    else:
        return len(encoding.encode(text))


def num_tokens_from_messages(messages: dict, model: str = "gpt-3.5-turbo-0613"):
    """Return the number of tokens used by a list of messages."""
    num_tokens = 0
    for message in messages:
        for key, value in message.items():
            _num_tokens, tokens_per_message, tokens_per_name = num_tokens_from_text(
                value, model=model, return_tokens_per_name_and_message=True
            )
            num_tokens += _num_tokens
            if key == "name":
                num_tokens += tokens_per_name
        num_tokens += tokens_per_message
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens


def split_text_to_chunks(
    text: str,
    max_tokens: int = 4000,
    chunk_mode: str = "multi_lines",
    must_break_at_empty_line: bool = True,
    overlap: int = 10,
):
    """Split a long text into chunks of max_tokens."""
    assert chunk_mode in {"one_line", "multi_lines"}
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


def split_files_to_chunks(
    files: list, max_tokens: int = 4000, chunk_mode: str = "multi_lines", must_break_at_empty_line: bool = True
):
    """Split a list of files into chunks of max_tokens."""
    chunks = []
    for file in files:
        with open(file, "r") as f:
            text = f.read()
        chunks += split_text_to_chunks(text, max_tokens, chunk_mode, must_break_at_empty_line)
    return chunks


def get_files_from_dir(dir_path: str, types: list = TEXT_FORMATS, recursive: bool = True):
    """Return a list of all the files in a given directory."""
    if len(types) == 0:
        raise ValueError("types cannot be empty.")
    types = [t[1:].lower() if t.startswith(".") else t.lower() for t in set(types)]
    types += [t.upper() for t in types]

    # If the path is a file, return it
    if os.path.isfile(dir_path):
        return [dir_path]

    # If the path is a url, download it and return the downloaded file
    if is_url(dir_path):
        return [get_file_from_url(dir_path)]

    files = []
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
        save_path = os.path.join("/tmp/chromadb", os.path.basename(url))
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
):
    """Create a vector db from all the files in a given directory."""
    if client is None:
        client = chromadb.PersistentClient(path=db_path)
    try:
        embedding_function = ef.SentenceTransformerEmbeddingFunction(embedding_model)
        collection = client.create_collection(
            collection_name,
            get_or_create=get_or_create,
            embedding_function=embedding_function,
            # https://github.com/nmslib/hnswlib#supported-distances
            # https://github.com/chroma-core/chroma/blob/566bc80f6c8ee29f7d99b6322654f32183c368c4/chromadb/segment/impl/vector/local_hnsw.py#L184
            # https://github.com/nmslib/hnswlib/blob/master/ALGO_PARAMS.md
            metadata={"hnsw:space": "ip", "hnsw:construction_ef": 30, "hnsw:M": 32},  # ip, l2, cosine
        )

        chunks = split_files_to_chunks(get_files_from_dir(dir_path), max_tokens, chunk_mode, must_break_at_empty_line)
        # updates existing items, or adds them if they don't yet exist.
        collection.upsert(
            documents=chunks,  # we handle tokenization, embedding, and indexing automatically. You can skip that and add your own embeddings as well
            ids=[f"doc_{i}" for i in range(len(chunks))],  # unique for each doc
        )
    except ValueError as e:
        logger.warning(f"{e}")


def query_vector_db(
    query_texts: List[str],
    n_results: int = 10,
    client: API = None,
    db_path: str = "/tmp/chromadb.db",
    collection_name: str = "all-my-documents",
    search_string: str = "",
    embedding_model: str = "all-MiniLM-L6-v2",
) -> Dict[str, List[str]]:
    """Query a vector db."""
    if client is None:
        client = chromadb.PersistentClient(path=db_path)
    # the collection's embedding function is always the default one, but we want to use the one we used to create the
    # collection. So we compute the embeddings ourselves and pass it to the query function.
    collection = client.get_collection(collection_name)
    embedding_function = ef.SentenceTransformerEmbeddingFunction(embedding_model)
    query_embeddings = embedding_function(query_texts)
    # Query/search n most similar results. You can also .get by id
    results = collection.query(
        query_embeddings=query_embeddings,
        n_results=n_results,
        where_document={"$contains": search_string} if search_string else None,  # optional filter
    )
    return results
