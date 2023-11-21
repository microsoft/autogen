from typing import Union, Optional, Callable, Dict, List
from pymongo import MongoClient
import pymongo
import openai

from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent


class MongoDBConfig:
    def __init__(self, mongo_url, database, vector_collection, vector_index, embedding_field):
        self.mongo_url = mongo_url
        self.database = database
        self.vector_collection = vector_collection
        self.vector_index = vector_index
        self.embedding_field = embedding_field


class MongoDBRetrieveUserProxyAgent(RetrieveUserProxyAgent):
    def __init__(
        self,
        mongo_config,
        name="RetrieveChatAgent",  # default set to RetrieveChatAgent
        human_input_mode: Optional[str] = "ALWAYS",
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        retrieve_config: Optional[Dict] = None,  # config for the retrieve agent
        **kwargs,
    ):
        super().__init__()
        self.mongo_config = mongo_config
        self._doc_ids = set()

    def query_vector_db(
        self,
        query_texts: List[str],
        n_results: int = 10,
        search_string: str = "",
        model="text-embedding-ada-002",
        **kwargs,
    ) -> Dict[str, Union[List[str], List[List[str]]]]:
        concatenated_text = " ".join(query_texts)
        embedding = self.get_embedding(concatenated_text, model=model)
        documents = self.find_similar_documents(embedding, n_results)
        ids = [str(idx) for idx in range(1, len(documents) + 1)]
        document_contents = [document.get("text_chunks", "") for document in documents]
        return {
            "ids": [ids],
            "documents": [document_contents],
        }

    def retrieve_docs(self, problem: str, n_results: int = 20, search_string: str = "", **kwargs):
        results = self.query_vector_db(
            query_texts=[problem],
            n_results=n_results,
            search_string=search_string,
            **kwargs,
        )
        self._results = results
        if isinstance(results["ids"], list) and len(results["ids"]) > 0 and isinstance(results["ids"][0], str):
            doc_id = results["ids"][0]
            if doc_id in self._doc_ids:
                for idx, document in enumerate(results["documents"]):
                    if isinstance(document, dict):
                        print(f"Document {idx + 1}: {document.get('text_chunks', '')}")
                    else:
                        print(f"Document {idx + 1}: {document}")
            else:
                print("No documents found.")

    def get_embedding(self, text, model="text-embedding-ada-002"):
        text = text.replace("\n", " ")
        return openai.Embedding.create(input=[text], model=model)["data"][0]["embedding"]

    def connect_mongodb(self):
        client = pymongo.MongoClient(self.mongo_config.mongo_url)
        db = client[self.mongo_config.database]
        collection = db[self.mongo_config.vector_collection]
        return collection

    def find_similar_documents(self, embedding, limit):
        collection = self.connect_mongodb()
        documents = list(
            collection.aggregate(
                [
                    {
                        "$vectorSearch": {
                            "index": self.mongo_config.vector_index,
                            "path": self.mongo_config.embedding_field,
                            "queryVector": embedding,
                            "numCandidates": 50,
                            "limit": limit,
                        }
                    }
                ]
            )
        )
        return documents
