import unittest
import pytest
import os
import sys


sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from conftest import skip_openai  # noqa: E402

try:
    from openai import OpenAI
    import sentence_transformers
    from autogen.agentchat.contrib.rag.rag_agent import RagAgent
except ImportError:
    skip = True
else:
    skip = False or skip_openai


here = os.path.abspath(os.path.dirname(__file__))


@pytest.mark.skipif(skip, reason="dependency is not installed OR requested to skip")
class TestRagAgent(unittest.TestCase):
    def test_init(self):
        agent = RagAgent(rag_config={"docs_path": os.path.join(here, "test_files")})
        self.assertEqual(agent.name, "rag_agent")
        self.assertEqual(agent.human_input_mode, "NEVER")
        self.assertFalse(agent.llm_config)
        self.assertEqual(agent.system_message, RagAgent.DEFAULT_RAG_SYSTEM_MESSAGE)
        self.assertEqual(agent.description, RagAgent.DEFAULT_RAG_SYSTEM_MESSAGE.strip("You're "))

    def test_init_with_config(self):
        rag_config = {
            "llm_model": "gpt-3.5-turbo-0613",
            "promptgen_n": 2,
            "top_k": 10,
            "filter_document": None,
            "filter_metadata": None,
            "include": None,
            "rag_llm_config": False,
            "max_token_ratio_for_context": 0.8,
            "splitter": "textline",
            "docs_path": os.path.join(here, "test_files"),
            "recursive": True,
            "chunk_size": 1024,
            "chunk_mode": "multi_lines",
            "must_break_at_empty_line": True,
            "overlap": 1,
            "token_count_function": lambda x: 1000,
            "max_token_limit": 1000,
            "custom_text_split_function": None,
            "embedding_function": "sentence_transformer",
            "retriever": "chroma",
            "collection_name": "autogen-rag",
            "db_path": "./tmp/{retriever}",
            "db_config": {},
            "overwrite": False,
            "get_or_create": True,
            "upsert": True,
            "reranker": "tfidf",
            "post_process_func": RagAgent.add_source_to_reply,
            "prompt_generator_post_process_func": None,
            "prompt_refine": None,
            "prompt_select": None,
            "prompt_rag": None,
            "enable_update_context": True,
        }
        agent = RagAgent(llm_config=False, rag_config=rag_config)
        self.assertEqual(agent.rag_config, rag_config)


if __name__ == "__main__":
    unittest.main()
