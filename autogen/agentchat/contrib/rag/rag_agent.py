import copy
from functools import partial
from termcolor import colored
from typing import Callable, Dict, Optional, Union, List, Tuple, Literal
from IPython import get_ipython
from autogen.agentchat import Agent, AssistantAgent, UserProxyAgent, ConversableAgent
from autogen.oai import OpenAIWrapper
from autogen.token_count_utils import count_token, get_max_token_limit
from autogen.code_utils import extract_code
from .datamodel import QueryResults, Query, ItemID, GetResults
from .promptgenerator import PromptGenerator
from .retriever import RetrieverFactory, Retriever
from .reranker import RerankerFactory, Reranker
from .encoder import Encoder, EmbeddingFunction, EmbeddingFunctionFactory
from .splitter import SplitterFactory, Splitter
from .utils import logger, timer, merge_and_get_unique_in_turn_same_length
from .constants import RAG_MINIMUM_MESSAGE_LENGTH


class RagAgent(ConversableAgent):
    """
    A RAG agent that can perform retrieval augmented generation for the given message.

    After receiving a message, the agent will perform RAG to generate a reply. It will retrieve documents
    based on the message, and then generate a reply based on the retrieved documents and the message. It
    also supports updating context automatically or triggered by the user during the conversation.

    There are a lot of configurations for the RAG agent. You can configure the RAG agent by providing a
    `rag_config` dictionary. For instance: rag_config = {"docs_path": "autogen/website/docs"}.
    Please refer to the constructor for more details.
    """

    DEFAULT_RAG_SYSTEM_MESSAGE = "You're a helpful AI assistant with retrieval augmented generation capability."

    def __init__(
        self,
        name="rag_agent",
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = 5,
        human_input_mode: Optional[str] = "NEVER",
        function_map: Optional[Dict[str, Callable]] = None,
        code_execution_config: Optional[Union[Dict, Literal[False]]] = None,
        default_auto_reply: Optional[Union[str, Dict, None]] = "",
        llm_config: Optional[Union[Dict, Literal[False]]] = False,
        system_message: Optional[Union[str, List]] = DEFAULT_RAG_SYSTEM_MESSAGE,
        description: Optional[str] = DEFAULT_RAG_SYSTEM_MESSAGE.strip("You're "),
        rag_config: Optional[Dict] = None,  # config for the rag agent
    ):
        """
        Args:
            name (str): name of the agent.
            is_termination_msg (function): a function that takes a message in the form of a dictionary
                and returns a boolean value indicating if this received message is a termination message.
                The dict can contain the following keys: "content", "role", "name", "function_call".
            max_consecutive_auto_reply (int): the maximum number of consecutive auto replies.
                default to None (no limit provided, class attribute MAX_CONSECUTIVE_AUTO_REPLY will be used as the limit in this case).
                When set to 0, no auto reply will be generated.
            human_input_mode (str): whether to ask for human inputs every time a message is received.
                Possible values are "ALWAYS", "TERMINATE", "NEVER".
                (1) When "ALWAYS", the agent prompts for human input every time a message is received.
                    Under this mode, the conversation stops when the human input is "exit",
                    or when is_termination_msg is True and there is no human input.
                (2) When "TERMINATE", the agent only prompts for human input only when a termination message is received or
                    the number of auto reply reaches the max_consecutive_auto_reply.
                (3) When "NEVER", the agent will never prompt for human input. Under this mode, the conversation stops
                    when the number of auto reply reaches the max_consecutive_auto_reply or when is_termination_msg is True.
            function_map (dict[str, callable]): Mapping function names (passed to openai) to callable functions, also used for tool calls.
            code_execution_config (dict or False): config for the code execution.
                To disable code execution, set to False. Otherwise, set to a dictionary with the following keys:
                - work_dir (Optional, str): The working directory for the code execution.
                    If None, a default working directory will be used.
                    The default working directory is the "extensions" directory under
                    "path_to_autogen".
                - use_docker (Optional, list, str or bool): The docker image to use for code execution.
                    Default is True, which means the code will be executed in a docker container. A default list of images will be used.
                    If a list or a str of image name(s) is provided, the code will be executed in a docker container
                    with the first image successfully pulled.
                    If False, the code will be executed in the current environment.
                    We strongly recommend using docker for code execution.
                - timeout (Optional, int): The maximum execution time in seconds.
                - last_n_messages (Experimental, int or str): The number of messages to look back for code execution.
                    If set to 'auto', it will scan backwards through all messages arriving since the agent last spoke, which is typically the last time execution was attempted. (Default: auto)
            default_auto_reply (str or dict): default auto reply when no code execution or llm-based reply is generated.
            llm_config (dict or False or None): llm inference configuration.
                Please refer to [OpenAIWrapper.create](/docs/reference/oai/client#create)
                for available options.
                To disable llm-based auto reply, set to False.
            system_message (str or list): system message for the ChatCompletion inference.
            description (str): a short description of the agent. This description is used by other agents
                (e.g. the GroupChatManager) to decide when to call upon this agent. (Default: system_message)
            rag_config (dict): config for the rag agent.
                - llm_model (str): the language model to use for the RAG agent. Default is "gpt-3.5-turbo-0613".
                - promptgen_n (int): the number of prompts to generate for each message. Default is 2.
                - top_k (int): the number of documents to retrieve for each prompt. Default is 10.
                - filter_document (str): the filter for the documents. Default is None.
                - filter_metadata (str): the filter for the metadata. Default is None.
                - include (str): the attributes to include in the query results. Default is None.
                - rag_llm_config (dict): the llm config for the RAG agent inner loop such as promptgenerator.
                    Default is the same as the llm_config. Set to False to disable promptgenerator.
                - max_token_ratio_for_context (float): the maximum token ratio for the context. Default is 0.8.
                - splitter (str or Splitter): the splitter to use for the RAG agent. Default is "textline".
                - docs_path (str): the path to the documents. Default is None.
                - recursive (bool): whether to recursively search for documents. Default is True.
                - chunk_size (int): the chunk size. Default is 1024.
                - chunk_mode (str): the chunk mode. Default is "multi_lines".
                - must_break_at_empty_line (bool): whether to break at empty line. Default is True.
                - overlap (int): the number of overlapping lines. Default is 1.
                - token_count_function (callable): the function to count the tokens. Default is count_token.
                - max_token_limit (int): the maximum token limit. Default is the maximum token limit for the llm model.
                - custom_text_split_function (callable): the custom text split function. Default is None.
                - embedding_function (str or EmbeddingFunction): the embedding function to use. Default is "sentence_transformer".
                - retriever (str or Retriever): the retriever to use. Default is "chroma".
                - collection_name (str): the collection name. Default is "autogen-rag".
                - db_path (str): the database path. Default is "./tmp/{retriever}".
                - db_config (dict): the database config. Default is {}.
                - overwrite (bool): whether to overwrite the collection. Default is False.
                - get_or_create (bool): whether to get or create the collection. Default is True.
                - upsert (bool): whether to upsert the documents. Default is True.
                - reranker (str or Reranker): the reranker to use. Default is "tfidf".
                - post_process_func (callable): the post process function. Default is self.add_source_to_reply.
                - prompt_generator_post_process_func (callable): the prompt generator post process function. Default is None.
                - prompt_refine (str): the prompt refine. Default is None.
                - prompt_select (str): the prompt select. Default is None.
                - prompt_rag (str): the prompt rag. Default is None.
                - enable_update_context (bool): whether to enable update context. Default is True.
                - customized_trigger_words (str): the customized trigger words. Default is "question".
                    If the message starts or ends with the trigger words, the context will be updated.
                - vector_db_get_is_fast (bool): whether the vector db get is fast. Default is True.
        """
        super().__init__(
            name=name,
            system_message=system_message,
            is_termination_msg=is_termination_msg,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            function_map=function_map,
            code_execution_config=code_execution_config,
            llm_config=llm_config,
            default_auto_reply=default_auto_reply,
            description=description,
        )
        self.rag_config = {} if rag_config is None else rag_config
        self.llm_model = self.rag_config.get("llm_model", "gpt-3.5-turbo-0613")
        self.rag_promptgen_n = self.rag_config.get("promptgen_n", 2)
        self.rag_top_k = self.rag_config.get("top_k", 10)
        self.rag_filter_document = self.rag_config.get("filter_document", None)
        self.rag_filter_metadata = self.rag_config.get("filter_metadata", None)
        self.rag_include = self.rag_config.get("include", None)  # attributes to include in the query results
        self.rag_llm_config = self.rag_config.get("rag_llm_config", copy.deepcopy(llm_config))
        self.max_token_ratio_for_context = self.rag_config.get("max_token_ratio_for_context", 0.8)

        # initialize the splitter
        self._splitter = self.rag_config.get("splitter", "textline")
        if isinstance(self._splitter, str):
            self.docs_path = self.rag_config.get("docs_path", None)
            self.recursive = self.rag_config.get("recursive", True)
            self.chunk_size = self.rag_config.get("chunk_size", 1024)
            self.chunk_mode = self.rag_config.get("chunk_mode", "multi_lines")
            self.must_break_at_empty_line = self.rag_config.get("must_break_at_empty_line", True)
            self.overlap = self.rag_config.get("overlap", 1)  # number of overlapping lines
            self.token_count_function = self.rag_config.get(
                "token_count_function", partial(count_token, model=self.llm_model)
            )
            self.max_token_limit = self.rag_config.get("max_token_limit", get_max_token_limit(self.llm_model))
            self.custom_text_split_function = self.rag_config.get("custom_text_split_function", None)
            self.splitter = SplitterFactory.create_splitter(
                self._splitter,
                self.docs_path,
                self.recursive,
                self.chunk_size,
                self.chunk_mode,
                self.must_break_at_empty_line,
                self.overlap,
                self.token_count_function,
                self.custom_text_split_function,
            )
        elif isinstance(self._splitter, Splitter):
            self.splitter = self._splitter
        else:
            raise ValueError(f"Invalid splitter: {self._splitter}.")

        # initialize the embedding function
        self._embedding_function = self.rag_config.get("embedding_function", "sentence_transformer")
        if isinstance(self._embedding_function, str):
            self.embedding_function = EmbeddingFunctionFactory.create_embedding_function(self._embedding_function)
        elif isinstance(self._embedding_function, EmbeddingFunction):
            self.embedding_function = self._embedding_function
        else:
            raise ValueError(f"Invalid embedding function: {self._embedding_function}.")

        # initialize the prompt generator
        self.prompt_generator_post_process_func = self.rag_config.get("prompt_generator_post_process_func", None)
        self.prompt_refine = self.rag_config.get("prompt_refine", None)
        self.prompt_select = self.rag_config.get("prompt_select", None)
        self.prompt_rag = self.rag_config.get("prompt_rag", None)
        self.prompt_generator = PromptGenerator(
            llm_config=self.rag_llm_config,
            prompt_rag=self.prompt_rag,
            prompt_refine=self.prompt_refine,
            prompt_select=self.prompt_select,
            post_process_func=self.prompt_generator_post_process_func,
        )

        # initialize the encoder
        self.encoder = Encoder(self.embedding_function)

        # initialize the retriever
        self._retriever = self.rag_config.get("retriever", "chroma")
        if isinstance(self._retriever, str):
            self.collection_name = self.rag_config.get("collection_name", "autogen-rag")
            self.db_path = self.rag_config.get("db_path", f"./tmp/{self._retriever}")
            self.db_config = self.rag_config.get("db_config", {})
            self.retriever = RetrieverFactory.create_retriever(
                self._retriever, self.collection_name, self.db_path, self.encoder, self.db_config
            )
        elif isinstance(self._retriever, Retriever):
            self.retriever = self._retriever
        else:
            raise ValueError(f"Invalid retriever: {self._retriever}.")

        # initialize the reranker
        self._reranker = self.rag_config.get("reranker", "tfidf")
        if isinstance(self._reranker, str):
            self.reranker = RerankerFactory.create_reranker(self._reranker)
        elif isinstance(self._reranker, Reranker):
            self.reranker = self._reranker
        else:
            raise ValueError(f"Invalid reranker: {self._reranker}.")

        # Chunk data and Create collection
        self.overwrite = self.rag_config.get("overwrite", False)
        self.get_or_create = self.rag_config.get("get_or_create", True)
        self.upsert = self.rag_config.get("upsert", True)

        if not self.splitter.docs_path:
            try:
                self.retriever.vector_db.get_collection(self.collection_name)
                logger.warning(
                    "`docs_path` is not provided for splitter. "
                    f"Use the existing collection `{self.collection_name}`.",
                    color="yellow",
                )
                self.overwrite = False
                self.get_or_create = True
                _docs = None
            except ValueError:
                raise ValueError(
                    "`docs_path` is not provided for splitter. "
                    f"The collection `{self.collection_name}` doesn't exist either. "
                    "Please provide `docs_path` or create the collection first."
                )
        elif self.get_or_create and not self.overwrite:
            try:
                self.retriever.vector_db.get_collection(self.collection_name)
                logger.info(f"Use the existing collection `{self.collection_name}`.", color="green")
                _docs = None
            except ValueError:
                # Chunk raw files
                _chunks = self.splitter.split()
                _docs = self.encoder.encode_chunks(_chunks)
        else:
            # Chunk raw files
            _chunks = self.splitter.split()
            _docs = self.encoder.encode_chunks(_chunks)
        self.retriever.vector_db.create_collection(self.collection_name, self.overwrite, self.get_or_create)
        self.retriever.vector_db.insert_docs(_docs, self.collection_name, upsert=self.upsert)

        # initialize the inner agents
        inner_llm_config = copy.deepcopy(llm_config)
        self._assistant = AssistantAgent(
            self.name + "_inner_assistant",
            system_message=system_message,
            llm_config=inner_llm_config,
            is_termination_msg=lambda m: False,
        )

        self._user_proxy = UserProxyAgent(
            self.name + "_inner_user_proxy",
            human_input_mode="NEVER",
            code_execution_config=False,
            default_auto_reply="",
            is_termination_msg=lambda m: False,
        )

        self.ipython = get_ipython()
        self.post_process_func = self.rag_config.get("post_process_func", self.add_source_to_reply)
        self.enable_update_context = self.rag_config.get("enable_update_context", True)
        self.customized_trigger_words = self.rag_config.get("customized_trigger_words", "question")
        self.vector_db_get_is_fast = self.rag_config.get("vector_db_get_is_fast", True)
        self.received_raw_message = None
        self.used_doc_ids = set()
        self.first_time = True

        # update the termination message function
        self._is_termination_msg = self._is_termination_msg_rag if is_termination_msg is None else is_termination_msg
        self.register_reply([Agent, None], RagAgent.generate_rag_reply, position=2)

    def _is_termination_msg_rag(self, message):
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

    def _merge_docs(self, query_results: QueryResults, key: str, unique_pos=None) -> Tuple[List[str], List[int]]:
        """
        Merge the documents in the query results.

        Args:
            query_results: QueryResults | The query results.
            key: str | The key to merge.
            unique_pos: List[int] | The unique positions.

        Returns:
            Tuple[List[str], List[int]] | The unique values and the unique positions.
        """
        _data = query_results.__getattribute__(key)
        if _data is not None:
            raw = merge_and_get_unique_in_turn_same_length(*_data)
        else:
            return None, None
        unique_value = []
        if unique_pos is None:
            unique_pos = []
            for idx, val in enumerate(raw):
                if val not in unique_value:
                    unique_value.append(val)
                    unique_pos.append(idx)
        else:
            for i in unique_pos:
                unique_value.append(raw[i])
        return unique_value, unique_pos

    def merge_documents(self, query_results: QueryResults) -> QueryResults:
        """
        Merge the documents in the query results.

        Args:
            query_results: QueryResults | The query results.

        Returns:
            QueryResults | The merged query results.
        """
        keys = QueryResults.__annotations__.keys()
        positions = None
        unique_values = {}
        for key in keys:
            unique_values[key], _positions = self._merge_docs(query_results, key, positions)
            if _positions:
                positions = _positions
        unique_values_without_used_ids = {}
        used_ids_positions = [
            i for i in range(len(unique_values["ids"])) if unique_values["ids"][i] in self.used_doc_ids
        ]
        for key in keys:
            if unique_values[key] is None:
                continue
            unique_values_without_used_ids[key] = [
                [unique_values[key][i] for i in range(len(unique_values[key])) if i not in used_ids_positions]
            ]
        return QueryResults(**unique_values_without_used_ids)

    def sort_query_results(self, query_results: QueryResults, order: List[int]) -> QueryResults:
        """
        Sort the query results based on the order.

        Args:
            query_results: QueryResults | The query results.
            order: List[int] | The order.

        Returns:
            QueryResults | The sorted query results.
        """
        keys = QueryResults.__annotations__.keys()
        sorted_values = {}
        for key in keys:
            if query_results.__getattribute__(key) is not None:
                sorted_values[key] = [[query_results.__getattribute__(key)[0][i] for i in order]]
        return QueryResults(**sorted_values)

    def merge_document_ids(self, query_results: QueryResults) -> List[ItemID]:
        """
        Merge the document ids in the query results.

        Args:
            query_results: QueryResults | The query results.

        Returns:
            List[ItemID] | The merged document ids.
        """
        ids = merge_and_get_unique_in_turn_same_length(*query_results.ids)
        return ids

    def sort_get_results_ids(self, get_results: GetResults, order: List[int]) -> List[ItemID]:
        """
        Sort the get results based on the order.

        Args:
            get_results: GetResults | The get results.
            order: List[int] | The order.

        Returns:
            List[ItemID] | The sorted document ids.
        """
        sorted_ids = [get_results.ids[i] for i in order]
        return sorted_ids

    def retrieve_rerank(self, raw_message: str, refined_questions: List[str]) -> QueryResults:
        """
        Retrieve and rerank the documents based on the refined questions.

        Args:
            raw_message: str | The raw message.
            refined_questions: List[str] | The refined questions.

        Returns:
            QueryResults | The query results.
        """
        length_used_doc_ids = len(self.used_doc_ids)
        queries = [
            Query(
                question,
                self.rag_top_k + length_used_doc_ids,
                self.rag_filter_metadata,
                self.rag_filter_document,
                self.rag_include,
            )
            for question in refined_questions
        ]
        retriever_query_results = self.retriever.retrieve_docs(queries)
        if self.vector_db_get_is_fast:
            retriever_deduplicated_ids = self.merge_document_ids(retriever_query_results)
            retriever_deduplicated_get_results = self.retriever.get_docs_by_ids(retriever_deduplicated_ids)
            reranked_order = self.reranker.rerank(
                Query(raw_message, self.rag_top_k * self.rag_promptgen_n + length_used_doc_ids),
                retriever_deduplicated_get_results.texts,
            )
            reranked_ids = self.sort_get_results_ids(retriever_deduplicated_get_results, reranked_order)
            reranked_query_results = self.retriever.convert_get_results_to_query_results(
                self.retriever.get_docs_by_ids(reranked_ids)
            )
        else:
            retriever_deduplicated_query_results = self.merge_documents(retriever_query_results)
            reranked_order = self.reranker.rerank(
                Query(raw_message, self.rag_top_k * self.rag_promptgen_n + length_used_doc_ids),
                retriever_deduplicated_query_results.texts[0],
            )
            reranked_query_results = self.sort_query_results(retriever_deduplicated_query_results, reranked_order)
        return reranked_query_results

    def check_update_context(self, message: str) -> Tuple[bool, str]:
        """Check if the message is to update the context.
        if yes, then return True and the new query string.
        if no, then return False and the input message.

        Args:
            message: str | The message.

        Returns:
            Tuple[bool, str] | The flag and the new message.
        """
        if isinstance(message, dict):
            message = message.get("content", "")
        elif not isinstance(message, str):
            message = ""
        trigger_words = ["update context", self.customized_trigger_words.lower()]
        for word in trigger_words:
            length_word = len(word) * 2
            if word in message[-length_word:].lower() or word in message[:length_word].lower():
                return True, message.lower().replace(word, "").strip()
        return False, message

    @timer
    def perform_rag(self, raw_message: str) -> None:
        """
        Perform retrieval augmented generation for the given message.
        """
        logger.debug(f"Performing RAG for message: {raw_message}", color="green")
        refined_questions, selected_prompt_rag = self.prompt_generator(raw_message, self.rag_promptgen_n)
        logger.debug(f"Refined message for db query: {refined_questions}", color="green")
        if self.received_raw_message not in refined_questions:
            refined_questions.append(self.received_raw_message)
        reranked_query_results = self.retrieve_rerank(raw_message, refined_questions)
        self.refined_questions = refined_questions
        self.selected_prompt_rag = selected_prompt_rag
        self.reranked_query_results = reranked_query_results

    def query_results_to_context(self, query_results: QueryResults, token_limits: int = -1) -> str:
        """
        Convert the query results to a context string.

        Args:
            query_results: QueryResults | The query results.
            token_limits: int | The token limits.

        Returns:
            str | The context string.
        """
        context = ""
        context_tokens = 0
        token_limits = self.max_token_limit * self.max_token_ratio_for_context if token_limits == -1 else token_limits
        self.current_docs_in_context = set()
        logger.debug(f"Used doc ids: {self.used_doc_ids}", color="green")
        for idx, doc in enumerate(query_results.texts[0]):
            doc_tokens = self.token_count_function(doc)
            if query_results.ids[0][idx] in self.used_doc_ids:
                continue
            if doc_tokens > token_limits:
                func_print = f"Skip doc_id {query_results.ids[0][idx]} as it is too long to fit in the context."
                logger.info(func_print, color="yellow")
                continue
            if context_tokens + doc_tokens > token_limits:
                break
            func_print = f"Adding doc_id {query_results.ids[0][idx]} to context."
            logger.debug(func_print, color="green")
            context += doc + "\n"
            context_tokens += doc_tokens
            self.used_doc_ids.add(query_results.ids[0][idx])
            self.current_docs_in_context.add(query_results.metadatas[0][idx].get("source", ""))
        return context

    @timer
    def process_message(self, message: str, tokens_in_history: int = 0) -> str:
        """
        Process the message and generate a reply.

        Args:
            message: str | The message.
            tokens_in_history: int | The tokens in history.

        Returns:
            str | The reply.
        """
        llm_message = ""
        token_limits = (self.max_token_limit - tokens_in_history) * self.max_token_ratio_for_context
        if self.first_time:
            self.perform_rag(message)
            context = self.query_results_to_context(self.reranked_query_results, token_limits)
            llm_message = self.selected_prompt_rag.format(input_question=message, input_context=context)
        else:
            is_update, new_message = self.check_update_context(message)
            logger.debug(
                f"Is update context: {is_update}, new message: {new_message[:100]}, length: {len(new_message)}"
            )
            if is_update:
                new_message = (
                    new_message if len(new_message) > RAG_MINIMUM_MESSAGE_LENGTH else self.received_raw_message
                )
                self.perform_rag(new_message)
                context = self.query_results_to_context(self.reranked_query_results, token_limits)
                llm_message = self.selected_prompt_rag.format(input_question=new_message, input_context=context)
            else:
                llm_message = ""
        return llm_message

    @staticmethod
    def count_messages_tokens(messages: List[Dict[str, str]]) -> int:
        """
        Count the total number of tokens in the messages.

        Args:
            messages: List[Dict[str, str]] | The messages.

        Returns:
            int | The total number of tokens.
        """
        return sum([count_token(msg["content"]) for msg in messages])

    @staticmethod
    def remove_old_context(messages: List[Dict[str, str]], token_limit: int = 1000) -> List[Dict[str, str]]:
        """
        Remove old context from the history.

        Args:
            messages: List[Dict[str, str]] | The messages.
            token_limit: int | The token limit.

        Returns:
            List[Dict[str, str]] | The new messages.
        """
        total_tokens = 0
        new_messages = []
        for msg in messages:
            _tokens = count_token(msg["content"])
            if _tokens <= token_limit:
                total_tokens += _tokens
                new_messages.append(msg)
        return new_messages, total_tokens

    def add_source_to_reply(self, reply: str) -> str:
        """Add the source of the document to the reply."""
        if not reply:
            return reply
        if not self.current_docs_in_context:
            return reply
        source = " ".join(self.current_docs_in_context)
        return f"{reply}\n\nSource: {source}"

    def _generate_llm_reply(
        self, message_to_llm: str, tokens_in_history: int = 0
    ) -> Tuple[str, Dict, Union[str, Dict], int]:
        """
        Generate a reply for the LLM agent.

        Args:
            message_to_llm: str | The message to the LLM agent.
            tokens_in_history: int | The tokens in history.

        Returns:
            Tuple[str, Dict, Union[str, Dict], int] | The LLM reply, the proxy reply, the tokens in history.
        """
        if message_to_llm:
            self._user_proxy.send(message_to_llm, self._assistant, request_reply=True, silent=True)
            llm_reply = self._user_proxy.chat_messages[self._assistant][-1]
            logger.debug(f"Inner LLM reply: {llm_reply}")
            self._assistant.chat_messages[self._user_proxy], tokens_in_history = self.remove_old_context(
                self._assistant.chat_messages[self._user_proxy]
            )
            proxy_reply = self._user_proxy.generate_reply(
                messages=self._user_proxy.chat_messages[self._assistant], sender=self._assistant
            )
            logger.debug(f"Inner proxy reply: {proxy_reply}")
        else:
            llm_reply = None
            proxy_reply = self._user_proxy.generate_reply(
                messages=self._user_proxy.chat_messages[self._assistant], sender=self._assistant
            )
            logger.debug(f"Inner proxy reply: {proxy_reply}")
        return llm_reply, proxy_reply, tokens_in_history

    def reset(self) -> None:
        """Reset the agent."""
        super().reset()
        self.used_doc_ids = set()
        self.received_raw_message = None
        self.first_time = True

    def generate_rag_reply(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        sender: Optional[Agent] = None,
        config: Optional[OpenAIWrapper] = None,
    ) -> Tuple[bool, Optional[Union[str, Dict[str, str]]]]:
        """
        Generate a reply for the RAG agent.

        Args:
            messages: List[Dict[str, str]] | The messages.
            sender: Agent | The sender.
            config: OpenAIWrapper | The OpenAI wrapper.

        Returns:
            Tuple[bool, Optional[Union[str, Dict[str, str]]]] | The flag and the reply.
        """
        if config is None:
            config = self
        if messages is None:
            messages = self._oai_messages[sender]

        self._assistant.reset()
        self._user_proxy.reset()

        # Clone the messages to give context
        self._assistant.chat_messages[self._user_proxy] = list()
        history = messages[0 : len(messages) - 1]
        for message in history:
            self._assistant.chat_messages[self._user_proxy].append(message)
            logger.debug(f"History message: {message}")
        tokens_in_history = self.count_messages_tokens(history)

        raw_message = messages[-1]["content"]
        self.received_raw_message = (
            raw_message
            if self.received_raw_message is None
            else (
                self.received_raw_message
                if self.check_update_context(raw_message)[0] or len(raw_message) < RAG_MINIMUM_MESSAGE_LENGTH
                else raw_message
            )
        )
        if raw_message == self.received_raw_message:
            self.used_doc_ids = set()
            self.first_time = True
        logger.debug(f"Input message: {raw_message}", color="green")
        logger.debug(f"Received raw message: {self.received_raw_message}", color="green")

        # Remind the agent of the raw question/task
        self._user_proxy.send(
            f"""In this chat, the original question/task for you is: `{self.received_raw_message}`""",
            self._assistant,
            request_reply=False,
            silent=True,
        )

        # RAG inner loop
        llm_reply = None
        while True:
            message_to_llm = self.process_message(
                llm_reply["content"] if llm_reply else raw_message, tokens_in_history=tokens_in_history
            )
            self.first_time = False
            logger.debug(f"To LLM message: {message_to_llm[:100]}", color="green")
            logger.debug(f"Tokens in history: {tokens_in_history}", color="green")

            if not message_to_llm:
                proxy_reply = ""
                break

            llm_reply, proxy_reply, tokens_in_history = self._generate_llm_reply(
                message_to_llm, tokens_in_history=tokens_in_history
            )
            if hasattr(self.prompt_generator, "error_message") and self.prompt_generator.error_message:
                logger.debug(f"Prompt generator error: {self.prompt_generator.error_message}")
                return True, self.prompt_generator.error_message

        if proxy_reply == "":  # default reply of the user proxy
            return True, (
                None
                if llm_reply is None
                else self.post_process_func(llm_reply["content"])
                if self.post_process_func
                else llm_reply["content"]
            )
        else:
            return True, None if proxy_reply is None else proxy_reply["content"]

    def run_code(self, code, **kwargs) -> Tuple[int, str, None]:
        """
        Run the code.

        Args:
            code: str | The code.
            kwargs: Dict | The keyword arguments.

        Returns:
            Tuple[int, str, None] | The exit code, the log, and the result.
        """
        lang = kwargs.get("lang", None)
        if code.startswith("!") or code.startswith("pip") or lang in ["bash", "shell", "sh"]:
            return (
                0,
                "You MUST NOT install any packages because all the packages needed are already installed.",
                None,
            )
        if self.ipython is None or lang != "python":
            return super().run_code(code, **kwargs)
        else:
            result = self.ipython.run_cell(code)
            log = str(result.result)
            exitcode = 0 if result.success else 1
            if result.error_before_exec is not None:
                log += f"\n{result.error_before_exec}"
                exitcode = 1
            if result.error_in_exec is not None:
                log += f"\n{result.error_in_exec}"
                exitcode = 1
            return exitcode, log, None
