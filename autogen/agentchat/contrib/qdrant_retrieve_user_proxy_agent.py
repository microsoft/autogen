from typing import Callable, Dict, List, Optional

from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent
from autogen.retrieve_utils import get_files_from_dir, split_files_to_chunks, TEXT_FORMATS
import logging

logger = logging.getLogger(__name__)

try:
    from qdrant_client import QdrantClient, models
    from qdrant_client.fastembed_common import QueryResponse
    import fastembed
except ImportError as e:
    logging.fatal("Failed to import qdrant_client with fastembed. Try running 'pip install qdrant_client[fastembed]'")
    raise e


class QdrantRetrieveUserProxyAgent(RetrieveUserProxyAgent):
    def __init__(
        self,
        name="RetrieveChatAgent",  # default set to RetrieveChatAgent
        human_input_mode: Optional[str] = "ALWAYS",
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        retrieve_config: Optional[Dict] = None,  # config for the retrieve agent
        **kwargs,
    ):
        """
        Args:
            name (str): name of the agent.
            human_input_mode (str): whether to ask for human inputs every time a message is received.
                Possible values are "ALWAYS", "TERMINATE", "NEVER".
                (1) When "ALWAYS", the agent prompts for human input every time a message is received.
                    Under this mode, the conversation stops when the human input is "exit",
                    or when is_termination_msg is True and there is no human input.
                (2) When "TERMINATE", the agent only prompts for human input only when a termination message is received or
                    the number of auto reply reaches the max_consecutive_auto_reply.
                (3) When "NEVER", the agent will never prompt for human input. Under this mode, the conversation stops
                    when the number of auto reply reaches the max_consecutive_auto_reply or when is_termination_msg is True.
            is_termination_msg (function): a function that takes a message in the form of a dictionary
                and returns a boolean value indicating if this received message is a termination message.
                The dict can contain the following keys: "content", "role", "name", "function_call".
            retrieve_config (dict or None): config for the retrieve agent.
                To use default config, set to None. Otherwise, set to a dictionary with the following keys:
                - task (Optional, str): the task of the retrieve chat. Possible values are "code", "qa" and "default". System
                    prompt will be different for different tasks. The default value is `default`, which supports both code and qa.
                - client (Optional, qdrant_client.QdrantClient(":memory:")): A QdrantClient instance. If not provided, an in-memory instance will be assigned. Not recommended for production.
                    will be used. If you want to use other vector db, extend this class and override the `retrieve_docs` function.
                - docs_path (Optional, Union[str, List[str]]): the path to the docs directory. It can also be the path to a single file,
                    the url to a single file or a list of directories, files and urls. Default is None, which works only if the collection is already created.
                - collection_name (Optional, str): the name of the collection.
                    If key not provided, a default name `autogen-docs` will be used.
                - model (Optional, str): the model to use for the retrieve chat.
                    If key not provided, a default model `gpt-4` will be used.
                - chunk_token_size (Optional, int): the chunk token size for the retrieve chat.
                    If key not provided, a default size `max_tokens * 0.4` will be used.
                - context_max_tokens (Optional, int): the context max token size for the retrieve chat.
                    If key not provided, a default size `max_tokens * 0.8` will be used.
                - chunk_mode (Optional, str): the chunk mode for the retrieve chat. Possible values are
                    "multi_lines" and "one_line". If key not provided, a default mode `multi_lines` will be used.
                - must_break_at_empty_line (Optional, bool): chunk will only break at empty line if True. Default is True.
                    If chunk_mode is "one_line", this parameter will be ignored.
                - embedding_model (Optional, str): the embedding model to use for the retrieve chat.
                    If key not provided, a default model `BAAI/bge-small-en-v1.5` will be used. All available models
                    can be found at `https://qdrant.github.io/fastembed/examples/Supported_Models/`.
                - customized_prompt (Optional, str): the customized prompt for the retrieve chat. Default is None.
                - customized_answer_prefix (Optional, str): the customized answer prefix for the retrieve chat. Default is "".
                    If not "" and the customized_answer_prefix is not in the answer, `Update Context` will be triggered.
                - update_context (Optional, bool): if False, will not apply `Update Context` for interactive retrieval. Default is True.
                - custom_token_count_function (Optional, Callable): a custom function to count the number of tokens in a string.
                    The function should take a string as input and return three integers (token_count, tokens_per_message, tokens_per_name).
                    Default is None, tiktoken will be used and may not be accurate for non-OpenAI models.
                - custom_text_split_function (Optional, Callable): a custom function to split a string into a list of strings.
                    Default is None, will use the default function in `autogen.retrieve_utils.split_text_to_chunks`.
                - custom_text_types (Optional, List[str]): a list of file types to be processed. Default is `autogen.retrieve_utils.TEXT_FORMATS`.
                    This only applies to files under the directories in `docs_path`. Explictly included files and urls will be chunked regardless of their types.
                - recursive (Optional, bool): whether to search documents recursively in the docs_path. Default is True.
                - parallel (Optional, int): How many parallel workers to use for embedding. Defaults to the number of CPU cores.
                - on_disk (Optional, bool): Whether to store the collection on disk. Default is False.
                - quantization_config: Quantization configuration. If None, quantization will be disabled.
                - hnsw_config: HNSW configuration. If None, default configuration will be used.
                  You can find more info about the hnsw configuration options at https://qdrant.tech/documentation/concepts/indexing/#vector-index.
                  API Reference: https://qdrant.github.io/qdrant/redoc/index.html#tag/collections/operation/create_collection
                - payload_indexing: Whether to create a payload index for the document field. Default is False.
                  You can find more info about the payload indexing options at https://qdrant.tech/documentation/concepts/indexing/#payload-index
                  API Reference: https://qdrant.github.io/qdrant/redoc/index.html#tag/collections/operation/create_field_index
             **kwargs (dict): other kwargs in [UserProxyAgent](../user_proxy_agent#__init__).

        """
        super().__init__(name, human_input_mode, is_termination_msg, retrieve_config, **kwargs)
        self._client = self._retrieve_config.get("client", QdrantClient(":memory:"))
        self._embedding_model = self._retrieve_config.get("embedding_model", "BAAI/bge-small-en-v1.5")
        # Uses all available CPU cores to encode data when set to 0
        self._parallel = self._retrieve_config.get("parallel", 0)
        self._on_disk = self._retrieve_config.get("on_disk", False)
        self._quantization_config = self._retrieve_config.get("quantization_config", None)
        self._hnsw_config = self._retrieve_config.get("hnsw_config", None)
        self._payload_indexing = self._retrieve_config.get("payload_indexing", False)

    def retrieve_docs(self, problem: str, n_results: int = 20, search_string: str = ""):
        """
        Args:
            problem (str): the problem to be solved.
            n_results (int): the number of results to be retrieved.
            search_string (str): only docs containing this string will be retrieved.
        """
        if not self._collection:
            print("Trying to create collection.")
            create_qdrant_from_dir(
                dir_path=self._docs_path,
                max_tokens=self._chunk_token_size,
                client=self._client,
                collection_name=self._collection_name,
                chunk_mode=self._chunk_mode,
                must_break_at_empty_line=self._must_break_at_empty_line,
                embedding_model=self._embedding_model,
                custom_text_split_function=self.custom_text_split_function,
                custom_text_types=self._custom_text_types,
                recursive=self._recursive,
                parallel=self._parallel,
                on_disk=self._on_disk,
                quantization_config=self._quantization_config,
                hnsw_config=self._hnsw_config,
                payload_indexing=self._payload_indexing,
            )
            self._collection = True

        results = query_qdrant(
            query_texts=problem,
            n_results=n_results,
            search_string=search_string,
            client=self._client,
            collection_name=self._collection_name,
            embedding_model=self._embedding_model,
        )
        self._results = results


def create_qdrant_from_dir(
    dir_path: str,
    max_tokens: int = 4000,
    client: QdrantClient = None,
    collection_name: str = "all-my-documents",
    chunk_mode: str = "multi_lines",
    must_break_at_empty_line: bool = True,
    embedding_model: str = "BAAI/bge-small-en-v1.5",
    custom_text_split_function: Callable = None,
    custom_text_types: List[str] = TEXT_FORMATS,
    recursive: bool = True,
    parallel: int = 0,
    on_disk: bool = False,
    quantization_config: Optional[models.QuantizationConfig] = None,
    hnsw_config: Optional[models.HnswConfigDiff] = None,
    payload_indexing: bool = False,
    qdrant_client_options: Optional[Dict] = {},
):
    """Create a Qdrant collection from all the files in a given directory, the directory can also be a single file or a
      url to a single file.

    Args:
        dir_path (str): the path to the directory, file or url.
        max_tokens (Optional, int): the maximum number of tokens per chunk. Default is 4000.
        client (Optional, QdrantClient): the QdrantClient instance. Default is None.
        collection_name (Optional, str): the name of the collection. Default is "all-my-documents".
        chunk_mode (Optional, str): the chunk mode. Default is "multi_lines".
        must_break_at_empty_line (Optional, bool): Whether to break at empty line. Default is True.
        embedding_model (Optional, str): the embedding model to use. Default is "BAAI/bge-small-en-v1.5".
            The list of all the available models can be at https://qdrant.github.io/fastembed/examples/Supported_Models/.
        custom_text_split_function (Optional, Callable): a custom function to split a string into a list of strings.
            Default is None, will use the default function in `autogen.retrieve_utils.split_text_to_chunks`.
        custom_text_types (Optional, List[str]): a list of file types to be processed. Default is TEXT_FORMATS.
        recursive (Optional, bool): whether to search documents recursively in the dir_path. Default is True.
        parallel (Optional, int): How many parallel workers to use for embedding. Defaults to the number of CPU cores
        on_disk (Optional, bool): Whether to store the collection on disk. Default is False.
        quantization_config: Quantization configuration. If None, quantization will be disabled.
            Ref: https://qdrant.github.io/qdrant/redoc/index.html#tag/collections/operation/create_collection
        hnsw_config: HNSW configuration. If None, default configuration will be used.
            Ref: https://qdrant.github.io/qdrant/redoc/index.html#tag/collections/operation/create_collection
        payload_indexing: Whether to create a payload index for the document field. Default is False.
        qdrant_client_options: (Optional, dict): the options for instantiating the qdrant client.
            Ref: https://github.com/qdrant/qdrant-client/blob/master/qdrant_client/qdrant_client.py#L36-L58.
    """
    if client is None:
        client = QdrantClient(**qdrant_client_options)
        client.set_model(embedding_model)

    if custom_text_split_function is not None:
        chunks = split_files_to_chunks(
            get_files_from_dir(dir_path, custom_text_types, recursive),
            custom_text_split_function=custom_text_split_function,
        )
    else:
        chunks = split_files_to_chunks(
            get_files_from_dir(dir_path, custom_text_types, recursive), max_tokens, chunk_mode, must_break_at_empty_line
        )
    logger.info(f"Found {len(chunks)} chunks.")

    # Check if collection by same name exists, if not, create it with custom options
    try:
        client.get_collection(collection_name=collection_name)
    except Exception:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=client.get_fastembed_vector_params(
                on_disk=on_disk, quantization_config=quantization_config, hnsw_config=hnsw_config
            ),
        )
        client.get_collection(collection_name=collection_name)

    # Upsert in batch of 100 or less if the total number of chunks is less than 100
    for i in range(0, len(chunks), min(100, len(chunks))):
        end_idx = i + min(100, len(chunks) - i)
        client.add(collection_name, documents=chunks[i:end_idx], ids=[j for j in range(i, end_idx)], parallel=parallel)

    # Create a payload index for the document field
    # Enables highly efficient payload filtering. Reference: https://qdrant.tech/documentation/concepts/indexing/#indexing
    # Creating an index requires additional computational resources and memory.
    # If filtering performance is critical, we can consider creating an index.
    if payload_indexing:
        client.create_payload_index(
            collection_name=collection_name,
            field_name="document",
            field_schema=models.TextIndexParams(
                type="text",
                tokenizer=models.TokenizerType.WORD,
                min_token_len=2,
                max_token_len=15,
            ),
        )


def query_qdrant(
    query_texts: List[str],
    n_results: int = 10,
    client: QdrantClient = None,
    collection_name: str = "all-my-documents",
    search_string: str = "",
    embedding_model: str = "BAAI/bge-small-en-v1.5",
    qdrant_client_options: Optional[Dict] = {},
) -> List[List[QueryResponse]]:
    """Perform a similarity search with filters on a Qdrant collection

    Args:
        query_texts (List[str]): the query texts.
        n_results (Optional, int): the number of results to return. Default is 10.
        client (Optional, API): the QdrantClient instance. A default in-memory client will be instantiated if None.
        collection_name (Optional, str): the name of the collection. Default is "all-my-documents".
        search_string (Optional, str): the search string. Default is "".
        embedding_model (Optional, str): the embedding model to use. Default is "all-MiniLM-L6-v2". Will be ignored if embedding_function is not None.
        qdrant_client_options: (Optional, dict): the options for instantiating the qdrant client. Reference: https://github.com/qdrant/qdrant-client/blob/master/qdrant_client/qdrant_client.py#L36-L58.

    Returns:
        List[List[QueryResponse]]: the query result. The format is:
            class QueryResponse(BaseModel, extra="forbid"):  # type: ignore
                id: Union[str, int]
                embedding: Optional[List[float]]
                metadata: Dict[str, Any]
                document: str
                score: float
    """
    if client is None:
        client = QdrantClient(**qdrant_client_options)
        client.set_model(embedding_model)

    results = client.query_batch(
        collection_name,
        query_texts,
        limit=n_results,
        query_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="document",
                    match=models.MatchText(text=search_string),
                )
            ]
        )
        if search_string
        else None,
    )

    data = {
        "ids": [[result.id for result in sublist] for sublist in results],
        "documents": [[result.document for result in sublist] for sublist in results],
    }
    return data
