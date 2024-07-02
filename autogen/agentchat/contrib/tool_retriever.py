import pandas as pd
from sentence_transformers import SentenceTransformer, util

from autogen import AssistantAgent, UserProxyAgent
from autogen.coding import LocalCommandLineCodeExecutor
from autogen.tool_utils import find_callables


class ToolBuilder:
    TOOL_USING_PROMPT = """# Functions
    You have access to the following functions. They can be accessed from the module called 'functions' by their function names.
For example, if there is a function called `foo` you could import it by writing `from functions import foo`

{functions}
"""

    def __init__(self, corpus_path, retriever):

        self.df = pd.read_csv(corpus_path, sep="\t")
        document_list = self.df["document_content"].tolist()

        self.model = SentenceTransformer(retriever)
        self.embeddings = self.model.encode(document_list)

    def retrieve(self, query, top_k=3):
        # Encode the query using the Sentence Transformer model
        query_embedding = self.model.encode([query])

        hits = util.semantic_search(query_embedding, self.embeddings, top_k=top_k)

        results = []
        for hit in hits[0]:
            results.append(self.df.iloc[hit["corpus_id"], 1])
        return results

    def bind(self, agent: AssistantAgent, functions: str):
        """Binds the function to the agent so that agent is aware of it."""
        sys_message = agent.system_message
        sys_message += self.TOOL_USING_PROMPT.format(functions=functions)
        agent.update_system_message(sys_message)
        return

    def bind_user_proxy(self, agent: UserProxyAgent, tool_root: str):
        """
        Updates user proxy agent with a executor so that code executor can successfully execute function-related code.
        Returns an updated user proxy.
        """
        # Find all the functions in the tool root
        functions = find_callables(tool_root)

        code_execution_config = agent._code_execution_config
        executor = LocalCommandLineCodeExecutor(
            timeout=code_execution_config.get("timeout", 180),
            work_dir=code_execution_config.get("work_dir", "coding"),
            functions=functions,
        )
        code_execution_config = {
            "executor": executor,
            "last_n_messages": code_execution_config.get("last_n_messages", 1),
        }
        updated_user_proxy = UserProxyAgent(
            name=agent.name,
            is_termination_msg=agent._is_termination_msg,
            code_execution_config=code_execution_config,
            human_input_mode="NEVER",
            default_auto_reply=agent._default_auto_reply,
        )
        return updated_user_proxy
