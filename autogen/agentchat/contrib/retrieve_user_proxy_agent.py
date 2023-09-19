import chromadb
from autogen.agentchat.agent import Agent
from autogen.agentchat import UserProxyAgent
from autogen.retrieve_utils import create_vector_db_from_dir, query_vector_db, num_tokens_from_text
from autogen.code_utils import extract_code

from typing import Callable, Dict, Optional, Union, List, Tuple, Any
from IPython import get_ipython

try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x


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


def _is_termination_msg_retrievechat(message):
    """Check if a message is a termination message."""
    if isinstance(message, dict):
        message = message.get("content")
        if message is None:
            return False
    cb = extract_code(message)
    contain_code = False
    for c in cb:
        if c[0] == "python":
            contain_code = True
            break
    return not contain_code


class RetrieveUserProxyAgent(UserProxyAgent):
    def __init__(
        self,
        name="RetrieveChatAgent",  # default set to RetrieveChatAgent
        is_termination_msg: Optional[Callable[[Dict], bool]] = _is_termination_msg_retrievechat,
        human_input_mode: Optional[str] = "ALWAYS",
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
            retrieve_config (dict or None): config for the retrieve agent.
                To use default config, set to None. Otherwise, set to a dictionary with the following keys:
                - task (Optional, str): the task of the retrieve chat. Possible values are "code", "qa" and "default". System
                    prompt will be different for different tasks. The default value is `default`, which supports both code and qa.
                - client (Optional, chromadb.Client): the chromadb client.
                    If key not provided, a default client `chromadb.Client()` will be used.
                - docs_path (Optional, str): the path to the docs directory. It can also be the path to a single file,
                    or the url to a single file. If key not provided, a default path `./docs` will be used.
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
                    If key not provided, a default model `all-MiniLM-L6-v2` will be used. All available models
                    can be found at `https://www.sbert.net/docs/pretrained_models.html`. The default model is a
                    fast model. If you want to use a high performance model, `all-mpnet-base-v2` is recommended.
                - customized_prompt (Optional, str): the customized prompt for the retrieve chat. Default is None.
            **kwargs (dict): other kwargs in [UserProxyAgent](../user_proxy_agent#__init__).
        """
        super().__init__(
            name=name,
            is_termination_msg=is_termination_msg,
            human_input_mode=human_input_mode,
            **kwargs,
        )

        self._retrieve_config = {} if retrieve_config is None else retrieve_config
        self._task = self._retrieve_config.get("task", "default")
        self._client = self._retrieve_config.get("client", chromadb.Client())
        self._docs_path = self._retrieve_config.get("docs_path", "./docs")
        self._collection_name = self._retrieve_config.get("collection_name", "autogen-docs")
        self._model = self._retrieve_config.get("model", "gpt-4")
        self._max_tokens = self.get_max_tokens(self._model)
        self._chunk_token_size = int(self._retrieve_config.get("chunk_token_size", self._max_tokens * 0.4))
        self._chunk_mode = self._retrieve_config.get("chunk_mode", "multi_lines")
        self._must_break_at_empty_line = self._retrieve_config.get("must_break_at_empty_line", True)
        self._embedding_model = self._retrieve_config.get("embedding_model", "all-MiniLM-L6-v2")
        self.customized_prompt = self._retrieve_config.get("customized_prompt", None)
        self._context_max_tokens = self._max_tokens * 0.8
        self._collection = False  # the collection is not created
        self._ipython = get_ipython()
        self._doc_idx = -1  # the index of the current used doc
        self._results = {}  # the results of the current query
        self.register_reply(Agent, RetrieveUserProxyAgent._generate_retrieve_user_reply)

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

    def _reset(self):
        self._doc_idx = -1  # the index of the current used doc
        self._results = {}  # the results of the current query

    def _get_context(self, results):
        doc_contents = ""
        current_tokens = 0
        _doc_idx = self._doc_idx
        for idx, doc in enumerate(results["documents"][0]):
            if idx <= _doc_idx:
                continue
            _doc_tokens = num_tokens_from_text(doc)
            if _doc_tokens > self._context_max_tokens:
                func_print = f"Skip doc_id {results['ids'][0][idx]} as it is too long to fit in the context."
                print(colored(func_print, "green"), flush=True)
                self._doc_idx = idx
                continue
            if current_tokens + _doc_tokens > self._context_max_tokens:
                break
            func_print = f"Adding doc_id {results['ids'][0][idx]} to context."
            print(colored(func_print, "green"), flush=True)
            current_tokens += _doc_tokens
            doc_contents += doc + "\n"
            self._doc_idx = idx
        return doc_contents

    def _generate_message(self, doc_contents, task="default"):
        if not doc_contents:
            print(colored("No more context, will terminate.", "green"), flush=True)
            return "TERMINATE"
        if self.customized_prompt:
            message = self.customized_prompt + "\nUser's question is: " + self.problem + "\nContext is: " + doc_contents
        elif task.upper() == "CODE":
            message = PROMPT_CODE.format(input_question=self.problem, input_context=doc_contents)
        elif task.upper() == "QA":
            message = PROMPT_QA.format(input_question=self.problem, input_context=doc_contents)
        elif task.upper() == "DEFAULT":
            message = PROMPT_DEFAULT.format(input_question=self.problem, input_context=doc_contents)
        else:
            raise NotImplementedError(f"task {task} is not implemented.")
        return message

    def _generate_retrieve_user_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        if config is None:
            config = self
        if messages is None:
            messages = self._oai_messages[sender]
        message = messages[-1]
        if (
            "UPDATE CONTEXT" in message.get("content", "")[-20:].upper()
            or "UPDATE CONTEXT" in message.get("content", "")[:20].upper()
        ):
            print(colored("Updating context and resetting conversation.", "green"), flush=True)
            self.clear_history()
            sender.clear_history()
            doc_contents = self._get_context(self._results)
            return True, self._generate_message(doc_contents, task=self._task)
        return False, None

    def retrieve_docs(self, problem: str, n_results: int = 20, search_string: str = ""):
        if not self._collection:
            create_vector_db_from_dir(
                dir_path=self._docs_path,
                max_tokens=self._chunk_token_size,
                client=self._client,
                collection_name=self._collection_name,
                chunk_mode=self._chunk_mode,
                must_break_at_empty_line=self._must_break_at_empty_line,
                embedding_model=self._embedding_model,
            )
            self._collection = True

        results = query_vector_db(
            query_texts=[problem],
            n_results=n_results,
            search_string=search_string,
            client=self._client,
            collection_name=self._collection_name,
            embedding_model=self._embedding_model,
        )
        self._results = results
        print("doc_ids: ", results["ids"])

    def generate_init_message(self, problem: str, n_results: int = 20, search_string: str = ""):
        """Generate an initial message with the given problem and prompt.

        Args:
            problem (str): the problem to be solved.
            n_results (int): the number of results to be retrieved.
            search_string (str): only docs containing this string will be retrieved.

        Returns:
            str: the generated prompt ready to be sent to the assistant agent.
        """
        self._reset()
        self.retrieve_docs(problem, n_results, search_string)
        self.problem = problem
        doc_contents = self._get_context(self._results)
        message = self._generate_message(doc_contents, self._task)
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
            # # capture may not work as expected
            # result = self._ipython.run_cell("%%capture --no-display cap\n" + code)
            # log = self._ipython.ev("cap.stdout")
            # log += self._ipython.ev("cap.stderr")
            # if result.result is not None:
            #     log += str(result.result)
            # exitcode = 0 if result.success else 1
            # if result.error_before_exec is not None:
            #     log += f"\n{result.error_before_exec}"
            #     exitcode = 1
            # if result.error_in_exec is not None:
            #     log += f"\n{result.error_in_exec}"
            #     exitcode = 1
            # return exitcode, log, None

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
