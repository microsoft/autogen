import hashlib
import os
import re
import uuid
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union

from IPython import get_ipython

try:
    import chromadb
except ImportError as e:
    raise ImportError(f"{e}. You can try `pip install pyautogen[retrievechat]`, or install `chromadb` manually.")
from autogen.agentchat import UserProxyAgent
from autogen.agentchat.agent import Agent
from autogen.agentchat.contrib.vectordb.base import Document, QueryResults, VectorDB, VectorDBFactory
from autogen.agentchat.contrib.vectordb.utils import (
    chroma_results_to_query_results,
    filter_results_by_distance,
    get_logger,
)
from autogen.code_utils import extract_code
from autogen.retrieve_utils import (
    TEXT_FORMATS,
    create_vector_db_from_dir,
    get_files_from_dir,
    query_vector_db,
    split_files_to_chunks,
)
from autogen.token_count_utils import count_token

from ...formatting_utils import colored

logger = get_logger(__name__)

PROMPT_DEFAULT = """You're a retrieve augmented chatbot. You answer user's questions based on your own knowledge and the
context provided by the user. You should follow the following steps to answer a question:
Step 1, you estimate the user's intent based on the question and context. The intent can be a code generation task or
a question answering task.
Step 2, you reply based on the intent.
If you can't answer the question with or without the current context, you should reply exactly `UPDATE CONTEXT`.
If user's intent is code generation, you must obey the following rules:
Rule 1. You MUST NOT install any packages because all the packages needed are already installed.
Rule 2. You must follow the formats below to write your code:
```language
# your code
```

If user's intent is question answering, you must give as short an answer as possible.

User's question is: {input_question}

Context is: {input_context}

The source of the context is: {input_sources}

If you can answer the question, in the end of your answer, add the source of the context in the format of `Sources: source1, source2, ...`.
"""

PROMPT_CODE = """You're a retrieve augmented coding assistant. You answer user's questions based on your own knowledge and the
context provided by the user.
If you can't answer the question with or without the current context, you should reply exactly `UPDATE CONTEXT`.
For code generation, you must obey the following rules:
Rule 1. You MUST NOT install any packages because all the packages needed are already installed.
Rule 2. You must follow the formats below to write your code:
```language
# your code
```

User's question is: {input_question}

Context is: {input_context}
"""

PROMPT_QA = """You're a retrieve augmented chatbot. You answer user's questions based on your own knowledge and the
context provided by the user.
If you can't answer the question with or without the current context, you should reply exactly `UPDATE CONTEXT`.
You must give as short an answer as possible.

User's question is: {input_question}

Context is: {input_context}
"""

HASH_LENGTH = int(os.environ.get("HASH_LENGTH", 8))
UPDATE_CONTEXT_IN_PROMPT = "you should reply exactly `UPDATE CONTEXT`"


class RetrieveUserProxyAgent(UserProxyAgent):
    """(In preview) The Retrieval-Augmented User Proxy retrieves document chunks based on the embedding
    similarity, and sends them along with the question to the Retrieval-Augmented Assistant
    """

    def __init__(
        self,
        name="RetrieveChatAgent",  # default set to RetrieveChatAgent
        human_input_mode: Literal["ALWAYS", "NEVER", "TERMINATE"] = "ALWAYS",
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        retrieve_config: Optional[Dict] = None,  # config for the retrieve agent
        **kwargs,
    ):
        r"""
        Args:
            name (str): name of the agent.

            human_input_mode (str): whether to ask for human inputs every time a message is received.
                Possible values are "ALWAYS", "TERMINATE", "NEVER".
                1. When "ALWAYS", the agent prompts for human input every time a message is received.
                    Under this mode, the conversation stops when the human input is "exit",
                    or when is_termination_msg is True and there is no human input.
                2. When "TERMINATE", the agent only prompts for human input only when a termination
                    message is received or the number of auto reply reaches
                    the max_consecutive_auto_reply.
                3. When "NEVER", the agent will never prompt for human input. Under this mode, the
                    conversation stops when the number of auto reply reaches the
                    max_consecutive_auto_reply or when is_termination_msg is True.

            is_termination_msg (function): a function that takes a message in the form of a dictionary
                and returns a boolean value indicating if this received message is a termination message.
                The dict can contain the following keys: "content", "role", "name", "function_call".

            retrieve_config (dict or None): config for the retrieve agent.

                To use default config, set to None. Otherwise, set to a dictionary with the
                following keys:
                - `task` (Optional, str) - the task of the retrieve chat. Possible values are
                    "code", "qa" and "default". System prompt will be different for different tasks.
                     The default value is `default`, which supports both code and qa, and provides
                     source information in the end of the response.
                - `vector_db` (Optional, Union[str, VectorDB]) - the vector db for the retrieve chat.
                    If it's a string, it should be the type of the vector db, such as "chroma"; otherwise,
                    it should be an instance of the VectorDB protocol. Default is "chroma".
                    Set `None` to use the deprecated `client`.
                - `db_config` (Optional, Dict) - the config for the vector db. Default is `{}`. Please make
                    sure you understand the config for the vector db you are using, otherwise, leave it as `{}`.
                    Only valid when `vector_db` is a string.
                - `client` (Optional, chromadb.Client) - the chromadb client. If key not provided, a
                     default client `chromadb.Client()` will be used. If you want to use other
                     vector db, extend this class and override the `retrieve_docs` function.
                     *[Deprecated]* use `vector_db` instead.
                - `docs_path` (Optional, Union[str, List[str]]) - the path to the docs directory. It
                     can also be the path to a single file, the url to a single file or a list
                     of directories, files and urls. Default is None, which works only if the
                     collection is already created.
                - `extra_docs` (Optional, bool) - when true, allows adding documents with unique IDs
                    without overwriting existing ones; when false, it replaces existing documents
                    using default IDs, risking collection overwrite., when set to true it enables
                    the system to assign unique IDs starting from "length+i" for new document
                    chunks, preventing the replacement of existing documents and facilitating the
                    addition of more content to the collection..
                    By default, "extra_docs" is set to false, starting document IDs from zero.
                    This poses a risk as new documents might overwrite existing ones, potentially
                    causing unintended loss or alteration of data in the collection.
                    *[Deprecated]* use `new_docs` when use `vector_db` instead of `client`.
                - `new_docs` (Optional, bool) - when True, only adds new documents to the collection;
                    when False, updates existing documents and adds new ones. Default is True.
                    Document id is used to determine if a document is new or existing. By default, the
                    id is the hash value of the content.
                - `model` (Optional, str) - the model to use for the retrieve chat.
                    If key not provided, a default model `gpt-4` will be used.
                - `chunk_token_size` (Optional, int) - the chunk token size for the retrieve chat.
                    If key not provided, a default size `max_tokens * 0.4` will be used.
                - `context_max_tokens` (Optional, int) - the context max token size for the
                    retrieve chat.
                    If key not provided, a default size `max_tokens * 0.8` will be used.
                - `chunk_mode` (Optional, str) - the chunk mode for the retrieve chat. Possible values
                    are "multi_lines" and "one_line". If key not provided, a default mode
                    `multi_lines` will be used.
                - `must_break_at_empty_line` (Optional, bool) - chunk will only break at empty line
                    if True. Default is True.
                    If chunk_mode is "one_line", this parameter will be ignored.
                - `embedding_model` (Optional, str) - the embedding model to use for the retrieve chat.
                    If key not provided, a default model `all-MiniLM-L6-v2` will be used. All available
                    models can be found at `https://www.sbert.net/docs/pretrained_models.html`.
                    The default model is a fast model. If you want to use a high performance model,
                    `all-mpnet-base-v2` is recommended.
                    *[Deprecated]* no need when use `vector_db` instead of `client`.
                - `embedding_function` (Optional, Callable) - the embedding function for creating the
                    vector db. Default is None, SentenceTransformer with the given `embedding_model`
                    will be used. If you want to use OpenAI, Cohere, HuggingFace or other embedding
                    functions, you can pass it here,
                    follow the examples in `https://docs.trychroma.com/embeddings`.
                - `customized_prompt` (Optional, str) - the customized prompt for the retrieve chat.
                    Default is None.
                - `customized_answer_prefix` (Optional, str) - the customized answer prefix for the
                    retrieve chat. Default is "".
                    If not "" and the customized_answer_prefix is not in the answer,
                    `Update Context` will be triggered.
                - `update_context` (Optional, bool) - if False, will not apply `Update Context` for
                    interactive retrieval. Default is True.
                - `collection_name` (Optional, str) - the name of the collection.
                    If key not provided, a default name `autogen-docs` will be used.
                - `get_or_create` (Optional, bool) - Whether to get the collection if it exists. Default is True.
                - `overwrite` (Optional, bool) - Whether to overwrite the collection if it exists. Default is False.
                    Case 1. if the collection does not exist, create the collection.
                    Case 2. the collection exists, if overwrite is True, it will overwrite the collection.
                    Case 3. the collection exists and overwrite is False, if get_or_create is True, it will get the collection,
                        otherwise it raise a ValueError.
                - `custom_token_count_function` (Optional, Callable) - a custom function to count the
                    number of tokens in a string.
                    The function should take (text:str, model:str) as input and return the
                    token_count(int). the retrieve_config["model"] will be passed in the function.
                    Default is autogen.token_count_utils.count_token that uses tiktoken, which may
                    not be accurate for non-OpenAI models.
                - `custom_text_split_function` (Optional, Callable) - a custom function to split a
                    string into a list of strings.
                    Default is None, will use the default function in
                    `autogen.retrieve_utils.split_text_to_chunks`.
                - `custom_text_types` (Optional, List[str]) - a list of file types to be processed.
                    Default is `autogen.retrieve_utils.TEXT_FORMATS`.
                    This only applies to files under the directories in `docs_path`. Explicitly
                    included files and urls will be chunked regardless of their types.
                - `recursive` (Optional, bool) - whether to search documents recursively in the
                    docs_path. Default is True.
                - `distance_threshold` (Optional, float) - the threshold for the distance score, only
                    distance smaller than it will be returned. Will be ignored if < 0. Default is -1.

            `**kwargs` (dict): other kwargs in [UserProxyAgent](../user_proxy_agent#__init__).

        Example:

        Example of overriding retrieve_docs - If you have set up a customized vector db, and it's
        not compatible with chromadb, you can easily plug in it with below code.
        *[Deprecated]* use `vector_db` instead. You can extend VectorDB and pass it to the agent.
        ```python
        class MyRetrieveUserProxyAgent(RetrieveUserProxyAgent):
            def query_vector_db(
                self,
                query_texts: List[str],
                n_results: int = 10,
                search_string: str = "",
                **kwargs,
            ) -> Dict[str, Union[List[str], List[List[str]]]]:
                # define your own query function here
                pass

            def retrieve_docs(self, problem: str, n_results: int = 20, search_string: str = "", **kwargs):
                results = self.query_vector_db(
                    query_texts=[problem],
                    n_results=n_results,
                    search_string=search_string,
                    **kwargs,
                )

                self._results = results
                print("doc_ids: ", results["ids"])
        ```
        """
        super().__init__(
            name=name,
            human_input_mode=human_input_mode,
            **kwargs,
        )

        self._retrieve_config = {} if retrieve_config is None else retrieve_config
        self._task = self._retrieve_config.get("task", "default")
        self._vector_db = self._retrieve_config.get("vector_db", "chroma")
        self._db_config = self._retrieve_config.get("db_config", {})
        self._client = self._retrieve_config.get("client", None)
        if self._client is None:
            self._client = chromadb.Client()
        self._docs_path = self._retrieve_config.get("docs_path", None)
        self._extra_docs = self._retrieve_config.get("extra_docs", False)
        self._new_docs = self._retrieve_config.get("new_docs", True)
        self._collection_name = self._retrieve_config.get("collection_name", "autogen-docs")
        if "docs_path" not in self._retrieve_config:
            logger.warning(
                "docs_path is not provided in retrieve_config. "
                f"Will raise ValueError if the collection `{self._collection_name}` doesn't exist. "
                "Set docs_path to None to suppress this warning."
            )
        self._model = self._retrieve_config.get("model", "gpt-4")
        self._max_tokens = self.get_max_tokens(self._model)
        self._chunk_token_size = int(self._retrieve_config.get("chunk_token_size", self._max_tokens * 0.4))
        self._chunk_mode = self._retrieve_config.get("chunk_mode", "multi_lines")
        self._must_break_at_empty_line = self._retrieve_config.get("must_break_at_empty_line", True)
        self._embedding_model = self._retrieve_config.get("embedding_model", "all-MiniLM-L6-v2")
        self._embedding_function = self._retrieve_config.get("embedding_function", None)
        self.customized_prompt = self._retrieve_config.get("customized_prompt", None)
        self.customized_answer_prefix = self._retrieve_config.get("customized_answer_prefix", "").upper()
        self.update_context = self._retrieve_config.get("update_context", True)
        self._get_or_create = self._retrieve_config.get("get_or_create", False) if self._docs_path is not None else True
        self._overwrite = self._retrieve_config.get("overwrite", False)
        self.custom_token_count_function = self._retrieve_config.get("custom_token_count_function", count_token)
        self.custom_text_split_function = self._retrieve_config.get("custom_text_split_function", None)
        self._custom_text_types = self._retrieve_config.get("custom_text_types", TEXT_FORMATS)
        self._recursive = self._retrieve_config.get("recursive", True)
        self._context_max_tokens = self._retrieve_config.get("context_max_tokens", self._max_tokens * 0.8)
        self._collection = True if self._docs_path is None else False  # whether the collection is created
        self._ipython = get_ipython()
        self._doc_idx = -1  # the index of the current used doc
        self._results = []  # the results of the current query
        self._intermediate_answers = set()  # the intermediate answers
        self._doc_contents = []  # the contents of the current used doc
        self._doc_ids = []  # the ids of the current used doc
        self._current_docs_in_context = []  # the ids of the current context sources
        self._search_string = ""  # the search string used in the current query
        self._distance_threshold = self._retrieve_config.get("distance_threshold", -1)
        # update the termination message function
        self._is_termination_msg = (
            self._is_termination_msg_retrievechat if is_termination_msg is None else is_termination_msg
        )
        if isinstance(self._vector_db, str):
            if not isinstance(self._db_config, dict):
                raise ValueError("`db_config` should be a dictionary.")
            if "embedding_function" in self._retrieve_config:
                self._db_config["embedding_function"] = self._embedding_function
            self._vector_db = VectorDBFactory.create_vector_db(db_type=self._vector_db, **self._db_config)
        self.register_reply(Agent, RetrieveUserProxyAgent._generate_retrieve_user_reply, position=2)

    def _init_db(self):
        if not self._vector_db:
            return

        IS_TO_CHUNK = False  # whether to chunk the raw files
        if self._new_docs:
            IS_TO_CHUNK = True
        if not self._docs_path:
            try:
                self._vector_db.get_collection(self._collection_name)
                logger.warning(f"`docs_path` is not provided. Use the existing collection `{self._collection_name}`.")
                self._overwrite = False
                self._get_or_create = True
                IS_TO_CHUNK = False
            except ValueError:
                raise ValueError(
                    "`docs_path` is not provided. "
                    f"The collection `{self._collection_name}` doesn't exist either. "
                    "Please provide `docs_path` or create the collection first."
                )
        elif self._get_or_create and not self._overwrite:
            try:
                self._vector_db.get_collection(self._collection_name)
                logger.info(f"Use the existing collection `{self._collection_name}`.", color="green")
            except ValueError:
                IS_TO_CHUNK = True
        else:
            IS_TO_CHUNK = True

        self._vector_db.active_collection = self._vector_db.create_collection(
            self._collection_name, overwrite=self._overwrite, get_or_create=self._get_or_create
        )

        docs = None
        if IS_TO_CHUNK:
            if self.custom_text_split_function is not None:
                chunks, sources = split_files_to_chunks(
                    get_files_from_dir(self._docs_path, self._custom_text_types, self._recursive),
                    custom_text_split_function=self.custom_text_split_function,
                )
            else:
                chunks, sources = split_files_to_chunks(
                    get_files_from_dir(self._docs_path, self._custom_text_types, self._recursive),
                    self._chunk_token_size,
                    self._chunk_mode,
                    self._must_break_at_empty_line,
                )
            logger.info(f"Found {len(chunks)} chunks.")

            if self._new_docs:
                all_docs_ids = set(
                    [
                        doc["id"]
                        for doc in self._vector_db.get_docs_by_ids(ids=None, collection_name=self._collection_name)
                    ]
                )
            else:
                all_docs_ids = set()

            chunk_ids = (
                [hashlib.blake2b(chunk.encode("utf-8")).hexdigest()[:HASH_LENGTH] for chunk in chunks]
                if not self._vector_db.type == "qdrant"
                else [str(uuid.UUID(hex=hashlib.md5(chunk.encode("utf-8")).hexdigest())) for chunk in chunks]
            )
            chunk_ids_set = set(chunk_ids)
            chunk_ids_set_idx = [chunk_ids.index(hash_value) for hash_value in chunk_ids_set]
            docs = [
                Document(id=chunk_ids[idx], content=chunks[idx], metadata=sources[idx])
                for idx in chunk_ids_set_idx
                if chunk_ids[idx] not in all_docs_ids
            ]

        self._vector_db.insert_docs(docs=docs, collection_name=self._collection_name, upsert=True)

    def _is_termination_msg_retrievechat(self, message):
        """Check if a message is a termination message.
        For code generation, terminate when no code block is detected. Currently only detect python code blocks.
        For question answering, terminate when don't update context, i.e., answer is given.
        """
        if isinstance(message, dict):
            message = message.get("content")
            if message is None:
                return False
        cb = extract_code(message)
        contain_code = False
        for c in cb:
            # todo: support more languages
            if c[0] == "python":
                contain_code = True
                break
        update_context_case1, update_context_case2 = self._check_update_context(message)
        return not (contain_code or update_context_case1 or update_context_case2)

    @staticmethod
    def get_max_tokens(model="gpt-3.5-turbo"):
        if "32k" in model:
            return 32000
        elif "16k" in model:
            return 16000
        elif "gpt-4" in model:
            return 8000
        else:
            return 4000

    def _reset(self, intermediate=False):
        self._doc_idx = -1  # the index of the current used doc
        self._results = []  # the results of the current query
        if not intermediate:
            self._intermediate_answers = set()  # the intermediate answers
            self._doc_contents = []  # the contents of the current used doc
            self._doc_ids = []  # the ids of the current used doc

    def _get_context(self, results: QueryResults):
        doc_contents = ""
        self._current_docs_in_context = []
        current_tokens = 0
        _doc_idx = self._doc_idx
        _tmp_retrieve_count = 0
        for idx, doc in enumerate(results[0]):
            doc = doc[0]
            if idx <= _doc_idx:
                continue
            if doc["id"] in self._doc_ids:
                continue
            _doc_tokens = self.custom_token_count_function(doc["content"], self._model)
            if _doc_tokens > self._context_max_tokens:
                func_print = f"Skip doc_id {doc['id']} as it is too long to fit in the context."
                print(colored(func_print, "green"), flush=True)
                self._doc_idx = idx
                continue
            if current_tokens + _doc_tokens > self._context_max_tokens:
                break
            func_print = f"Adding content of doc {doc['id']} to context."
            print(colored(func_print, "green"), flush=True)
            current_tokens += _doc_tokens
            doc_contents += doc["content"] + "\n"
            _metadata = doc.get("metadata")
            if isinstance(_metadata, dict):
                self._current_docs_in_context.append(_metadata.get("source", ""))
            self._doc_idx = idx
            self._doc_ids.append(doc["id"])
            self._doc_contents.append(doc["content"])
            _tmp_retrieve_count += 1
            if _tmp_retrieve_count >= self.n_results:
                break
        return doc_contents

    def _generate_message(self, doc_contents, task="default"):
        if not doc_contents:
            print(colored("No more context, will terminate.", "green"), flush=True)
            return "TERMINATE"
        if self.customized_prompt:
            message = self.customized_prompt.format(input_question=self.problem, input_context=doc_contents)
        elif task.upper() == "CODE":
            message = PROMPT_CODE.format(input_question=self.problem, input_context=doc_contents)
        elif task.upper() == "QA":
            message = PROMPT_QA.format(input_question=self.problem, input_context=doc_contents)
        elif task.upper() == "DEFAULT":
            message = PROMPT_DEFAULT.format(
                input_question=self.problem, input_context=doc_contents, input_sources=self._current_docs_in_context
            )
        else:
            raise NotImplementedError(f"task {task} is not implemented.")
        return message

    def _check_update_context(self, message):
        if isinstance(message, dict):
            message = message.get("content", "")
        elif not isinstance(message, str):
            message = ""
        update_context_case1 = "UPDATE CONTEXT" in message.upper() and UPDATE_CONTEXT_IN_PROMPT not in message
        update_context_case2 = self.customized_answer_prefix and self.customized_answer_prefix not in message.upper()
        return update_context_case1, update_context_case2

    def _generate_retrieve_user_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        """In this function, we will update the context and reset the conversation based on different conditions.
        We'll update the context and reset the conversation if update_context is True and either of the following:
        (1) the last message contains "UPDATE CONTEXT",
        (2) the last message doesn't contain "UPDATE CONTEXT" and the customized_answer_prefix is not in the message.
        """
        if config is None:
            config = self
        if messages is None:
            messages = self._oai_messages[sender]
        message = messages[-1]
        update_context_case1, update_context_case2 = self._check_update_context(message)
        if (update_context_case1 or update_context_case2) and self.update_context:
            print(colored("Updating context and resetting conversation.", "green"), flush=True)
            # extract the first sentence in the response as the intermediate answer
            _message = message.get("content", "").split("\n")[0].strip()
            _intermediate_info = re.split(r"(?<=[.!?])\s+", _message)
            self._intermediate_answers.add(_intermediate_info[0])

            if update_context_case1:
                # try to get more context from the current retrieved doc results because the results may be too long to fit
                # in the LLM context.
                doc_contents = self._get_context(self._results)

                # Always use self.problem as the query text to retrieve docs, but each time we replace the context with the
                # next similar docs in the retrieved doc results.
                if not doc_contents:
                    for _tmp_retrieve_count in range(1, 5):
                        self._reset(intermediate=True)
                        self.retrieve_docs(
                            self.problem, self.n_results * (2 * _tmp_retrieve_count + 1), self._search_string
                        )
                        doc_contents = self._get_context(self._results)
                        if doc_contents:
                            break
            elif update_context_case2:
                # Use the current intermediate info as the query text to retrieve docs, and each time we append the top similar
                # docs in the retrieved doc results to the context.
                for _tmp_retrieve_count in range(5):
                    self._reset(intermediate=True)
                    self.retrieve_docs(
                        _intermediate_info[0], self.n_results * (2 * _tmp_retrieve_count + 1), self._search_string
                    )
                    self._get_context(self._results)
                    doc_contents = "\n".join(self._doc_contents)  # + "\n" + "\n".join(self._intermediate_answers)
                    if doc_contents:
                        break

            self.clear_history()
            sender.clear_history()
            return True, self._generate_message(doc_contents, task=self._task)
        else:
            return False, None

    def retrieve_docs(self, problem: str, n_results: int = 20, search_string: str = ""):
        """Retrieve docs based on the given problem and assign the results to the class property `_results`.
        The retrieved docs should be type of `QueryResults` which is a list of tuples containing the document and
        the distance.

        Args:
            problem (str): the problem to be solved.
            n_results (int): the number of results to be retrieved. Default is 20.
            search_string (str): only docs that contain an exact match of this string will be retrieved. Default is "".
                Not used if the vector_db doesn't support it.

        Returns:
            None.
        """
        if isinstance(self._vector_db, VectorDB):
            if not self._collection or not self._get_or_create:
                print("Trying to create collection.")
                self._init_db()
                self._collection = True
                self._get_or_create = True

            kwargs = {}
            if hasattr(self._vector_db, "type") and self._vector_db.type == "chroma":
                kwargs["where_document"] = {"$contains": search_string} if search_string else None
            results = self._vector_db.retrieve_docs(
                queries=[problem],
                n_results=n_results,
                collection_name=self._collection_name,
                distance_threshold=self._distance_threshold,
                **kwargs,
            )
            self._search_string = search_string
            self._results = results
            print("VectorDB returns doc_ids: ", [[r[0]["id"] for r in rr] for rr in results])
            return

        if not self._collection or not self._get_or_create:
            print("Trying to create collection.")
            self._client = create_vector_db_from_dir(
                dir_path=self._docs_path,
                max_tokens=self._chunk_token_size,
                client=self._client,
                collection_name=self._collection_name,
                chunk_mode=self._chunk_mode,
                must_break_at_empty_line=self._must_break_at_empty_line,
                embedding_model=self._embedding_model,
                get_or_create=self._get_or_create,
                embedding_function=self._embedding_function,
                custom_text_split_function=self.custom_text_split_function,
                custom_text_types=self._custom_text_types,
                recursive=self._recursive,
                extra_docs=self._extra_docs,
            )
            self._collection = True
            self._get_or_create = True

        results = query_vector_db(
            query_texts=[problem],
            n_results=n_results,
            search_string=search_string,
            client=self._client,
            collection_name=self._collection_name,
            embedding_model=self._embedding_model,
            embedding_function=self._embedding_function,
        )
        results["contents"] = results.pop("documents")
        results = chroma_results_to_query_results(results, "distances")
        results = filter_results_by_distance(results, self._distance_threshold)

        self._search_string = search_string
        self._results = results
        print("doc_ids: ", [[r[0]["id"] for r in rr] for rr in results])

    @staticmethod
    def message_generator(sender, recipient, context):
        """
        Generate an initial message with the given context for the RetrieveUserProxyAgent.
        Args:
            sender (Agent): the sender agent. It should be the instance of RetrieveUserProxyAgent.
            recipient (Agent): the recipient agent. Usually it's the assistant agent.
            context (dict): the context for the message generation. It should contain the following keys:
                - `problem` (str) - the problem to be solved.
                - `n_results` (int) - the number of results to be retrieved. Default is 20.
                - `search_string` (str) - only docs that contain an exact match of this string will be retrieved. Default is "".
        Returns:
            str: the generated message ready to be sent to the recipient agent.
        """
        sender._reset()

        problem = context.get("problem", "")
        n_results = context.get("n_results", 20)
        search_string = context.get("search_string", "")

        sender.retrieve_docs(problem, n_results, search_string)
        sender.problem = problem
        sender.n_results = n_results
        doc_contents = sender._get_context(sender._results)
        message = sender._generate_message(doc_contents, sender._task)
        return message

    def run_code(self, code, **kwargs):
        lang = kwargs.get("lang", None)
        if code.startswith("!") or code.startswith("pip") or lang in ["bash", "shell", "sh"]:
            return (
                0,
                "You MUST NOT install any packages because all the packages needed are already installed.",
                None,
            )
        if self._ipython is None or lang != "python":
            return super().run_code(code, **kwargs)
        else:
            result = self._ipython.run_cell(code)
            log = str(result.result)
            exitcode = 0 if result.success else 1
            if result.error_before_exec is not None:
                log += f"\n{result.error_before_exec}"
                exitcode = 1
            if result.error_in_exec is not None:
                log += f"\n{result.error_in_exec}"
                exitcode = 1
            return exitcode, log, None
