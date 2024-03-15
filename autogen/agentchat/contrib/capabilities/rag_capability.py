import os
from autogen.agentchat.assistant_agent import ConversableAgent
from autogen.agentchat.contrib.capabilities.agent_capability import AgentCapability
from autogen.agentchat.contrib.rag import RagAgent, logger
from autogen.agentchat.contrib.rag.prompts import PROMPT_CAPABILITIES
from typing import Dict, Optional, Union, List, Tuple, Any, Literal


class Ragability(AgentCapability):
    """
    Ragability gives an agent the ability to reply with RAG (Retrieval-Augmented Generation),
    where the user is any caller (human or not) sending messages to the ragable agent.
    Ragability is designed to be composable with other agent capabilities.
    To make any conversable agent ragable, instantiate both the agent and the Ragability class,
    then pass the agent to ragability.add_to_agent(agent).
    """

    def __init__(
        self,
        verbose: int = 1,
        max_consecutive_auto_reply: Optional[int] = 5,
        llm_config: Optional[Union[Dict, Literal[False]]] = False,
        rag_config: Optional[Dict] = None,  # config for the ragability
        rag_to_agent_prompt: Optional[str] = None,
    ):
        """
        Args:
            verbose (Optional, int): 0 for basic info, 1 for RAG agent info, 2 for debug info. Default is 1.
            max_consecutive_auto_reply (int): the maximum number of consecutive auto replies for the RAG agent. Default is 5.
            llm_config (dict or False or None): llm inference configuration.
                Please refer to [OpenAIWrapper.create](/docs/reference/oai/client#create)
                for available options.
                To disable llm-based auto reply, set to False.
            rag_config (dict): config for the rag agent.
                - llm_model (str): the language model to use for the RAG agent, it's used to count tokens.
                    Default is llm_config["config_list"][0]["model"] or "gpt-3.5-turbo-0613".
                - promptgen_n (int): the number of refined messages to generate for each message. Default is 2.
                - top_k (int): the number of documents to retrieve for each refined message. Default is 10.
                - filter_document (str): the filter for the documents, the usage would differ for different vector database.
                    Default is None. For chromadb, `{"$contains": "spark"}` means to retrieve documents that contain "spark".
                - filter_metadata (str): the filter for the metadata, the usage would differ for different vector database.
                    Default is None. For chromadb, `{"color" : "red"}` means to retrieve documents with metadata "color" equals to "red".
                - include (str): the attributes to include in the query results. Default is ["metadatas", "documents", "distances"]
                - rag_llm_config (dict): the llm config for the RAG agent inner loop such as promptgenerator. Default is
                    the same as the llm_config. Set to False to disable promptgenerator (prompts selection and message refinement).
                - max_token_ratio_for_context (float): the maximum token ratio for the context, used to control the
                    number of tokens in the input of LLM calls. Default is 0.8.
                - splitter (str or Splitter): the splitter to use for the RAG agent. Default is "textline" which will use
                    the built-in `TextLineSplitter` to split the text into lines. The splitter can be set to an instance
                    of `Splitter` as well. Extend the `Splitter` class to create a custom splitter.
                - docs_path (str): the path to the raw files for building the knowledge base. Default is None. If not
                    provided, it will use the existing collection if it exists, otherwise it will raise an ValueError.
                - recursive (bool): whether to recursively search for files in the `docs_path`. Default is True.
                - chunk_size (int): the maximum number of tokens of each chunk. Default is 1024.
                - chunk_mode (str): the chunk mode. Default is "multi_lines". Other option is "one_line".
                - must_break_at_empty_line (bool): whether to break at empty line. Default is True.
                - overlap (int): the number of overlapping lines. Default is 1.
                - token_count_function (callable): the function to count the tokens. Default is `autogen.token_count_utils.count_token`.
                    Pass a custom function to count the tokens if needed.
                - max_token_limit (int): the maximum token limit of the conversation. Default is the maximum token limit for the llm model.
                - custom_text_split_function (callable): the custom text split function. Default is None.
                - embedding_function (str or EmbeddingFunction): the embedding function to use. Default is "sentence_transformer".
                - retriever (str or Retriever): the retriever to use. Default is "chroma", will use the built-in `ChromaRetriever`.
                    The retriever can be set to an instance of `Retriever` as well. Extend the `Retriever` class to create a custom retriever.
                - collection_name (str): the collection name for the vector database. Default is "autogen-rag".
                - db_path (str): the database path. Default is "./tmp/{retriever}". Invalid if retriever is an instance of `Retriever`.
                - db_config (dict): the database config. Default is {}. The value will be different for different vector database.
                - overwrite (bool): whether to overwrite the collection. Default is False. If True, will overwrite the
                    collection if it exists or create a new collection if it doesn't exist.
                - get_or_create (bool): whether to get or create the collection. Default is True. If True, will reuse the
                    existing collection if it exists, otherwise will create a new collection. If False, will create a new
                    collection if it doesn't exist, otherwise will raise an ValueError. Invalid if overwrite is True.
                - upsert (bool): whether to upsert the documents. Default is True. If False, existing documents will not be updated.
                - reranker (str or Reranker): the reranker to use. Default is "tfidf", which uses the built-in `TfidfReranker`.
                    The reranker can be set to an instance of `Reranker` as well. Extend the `Reranker` class to create a custom reranker.
                - post_process_func (callable): the post process function. Default is `add_source_to_reply` which simply
                    adds the sources of the context to the end of the reply.
                - prompt_generator_post_process_func (callable): the post process function for PromptGenerator. Default is None,
                    will use the built-in `promptgenerator.extract_refined_questions`.
                - prompt_refine (str): the prompt for refining the received message. Default is None, will use the
                    built-in `prompts.PROMPTS_GENERATOR["refine"]`.
                - prompt_select (str): the prompt for selecting the best prompts for replying the received message.
                    Default is None, will use the built-in `prompts.PROMPTS_GENERATOR["select"]`.
                - prompt_rag (str): the prompt for sending requests to LLM backend. Default is None, one of the built-in
                    `prompts.PROMPTS_RAG` will be selected by `PromptGenerator`.
                - enable_update_context (bool): whether to enable update context. Default is True. If True, the context will
                    be updated if the message starts or ends with the trigger words.
                - customized_trigger_words (Union[str, List[str]]): the customized trigger words, case insensitive.
                    Default is ["update context", "question"]. If the message starts or ends with the trigger words,
                    the context will be updated.
                - vector_db_get_is_fast (bool): whether the vector db get is fast. If True, will save some memory w/o
                    introducing much latency. Default is True. Set to False if the vector db has high latency.
            rag_to_agent_prompt (Optional, str): the prompt for refine the rag reply to the agent. Default is built-in
                `PROMPT_CAPABILITIES` in rag module. The prompt should contain `{text}` and `{rag_reply}`.
        """
        self.llm_config = llm_config
        self.rag_config = rag_config
        self.max_consecutive_auto_reply = max_consecutive_auto_reply
        self.ragagent = None
        self.ragable_agent = None
        self.verbose = verbose
        self.prompt = rag_to_agent_prompt or PROMPT_CAPABILITIES
        if "{text}" not in self.prompt or "{rag_reply}" not in self.prompt:
            raise ValueError("rag_to_agent_prompt should contain both {text} and {rag_reply}.")
        if verbose >= 2:
            logger.setLevel("DEBUG")

    def add_to_agent(self, agent: ConversableAgent):
        """Adds ragability to the given agent."""

        # Register a hook for processing the last message.
        agent.register_hook(hookable_method="process_last_received_message", hook=self.process_last_received_message)

        # Was an llm_config passed to the constructor?
        if self.llm_config is None:
            # No. Use the agent's llm_config.
            self.llm_config = agent.llm_config
        assert self.llm_config, "Ragability requires a valid llm_config."

        # Create the rag agent.
        self.ragagent = RagAgent(
            llm_config=self.llm_config,
            rag_config=self.rag_config,
            max_consecutive_auto_reply=self.max_consecutive_auto_reply,
            code_execution_config=False,
        )

        # Append extra info to the system message.
        agent.update_system_message(
            agent.system_message
            + "\nYou've been given the special ability to perform retrieval augmented generation (RAG) for replying a message. "
            + "You can answer questions, solve problems based on a knowledge base."
        )
        self.ragable_agent = agent

    def process_last_received_message(self, text: str) -> str:
        """
        Generates a response to the last received message using the RAG agent.
        """

        if not text:
            return text

        self.ragagent.reset()  # Reset the RAG agent.
        self.ragable_agent.send(recipient=self.ragagent, message=text, request_reply=True, silent=(self.verbose < 1))
        rag_reply = self.ragable_agent.last_message(self.ragagent).get("content")
        rag_reply = self.prompt.format(text=text, rag_reply=rag_reply)
        # logger.debug(f"Ragability RAG agent replied with: {rag_reply}")
        return rag_reply
