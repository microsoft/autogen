import autogen
from autogen import AssistantAgent, UserProxyAgent, config_list_from_json
from autogen.agentchat.contrib.retrieve_assistant_agent import RetrieveAssistantAgent
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent
from typing import List, Dict, Union
from pymongo import MongoClient
import pymongo
import openai

# Load the configuration from JSON file
config_list = config_list_from_json(env_or_file="llm_config")


class MongoDBRetrieveUserProxyAgent(RetrieveUserProxyAgent):
    def query_vector_db(
        self,
        query_texts: List[str],
        n_results: int = 10,
        search_string: str = "",
        **kwargs,
    ) -> Dict[str, Union[List[str], List[List[str]]]]:
        # Concatenate all strings in query_texts into one string
        concatenated_text = " ".join(query_texts)

        # Get the embedding from MongoDB
        embedding = self.get_embedding(concatenated_text)

        # Find similar documents in MongoDB
        documents = self.find_similar_documents(embedding)
        ids = [str(idx) for idx in range(1, len(documents) + 1)]
        document_contents = [document.get(
            "text_chunks", "") for document in documents]
        return {
            "ids": [ids],       # Wrap ids in a list
            # Wrap document_contents in a list
            "documents": [document_contents],
        }

    def retrieve_docs(self, problem: str, n_results: int = 20, search_string: str = "", **kwargs):
        # Query for similar documents
        results = self.query_vector_db(
            query_texts=[problem],
            n_results=n_results,
            search_string=search_string,
            **kwargs,
        )
        self._results = results

        # Check if results is a dictionary and "documents" is a list
        if isinstance(results["ids"], list) and len(results["ids"]) > 0 and isinstance(results["ids"][0], str):
            doc_id = results["ids"][0]
            if doc_id in self._doc_ids:
                # Accessing the "documents" key in the results dictionary
                for idx, document in enumerate(results["documents"]):
                    if isinstance(document, dict):
                        print(
                            f"Document {idx + 1}: {document.get('text_chunks', '')}")
                    else:
                        print(f"Document {idx + 1}: {document}")
            else:
                print("No documents found.")

    def get_embedding(self, text, model="text-embedding-ada-002"):
        """
        Get the embedding for a given text using OpenAI's API.
        """
        text = text.replace("\n", " ")
        return openai.Embedding.create(input=[text], model=model)['data'][0]['embedding']

    def connect_mongodb(self):
        """
        Connect to the MongoDB Atlas server and return the collection. 

        Initiate your connection to a MongoDB Atlas server and access your desired collection directly. 
        I recommend getting started with an M0 tier of MongoDB which is free of charge and fully managed. You can sign up here: <https://www.mongodb.com/cloud/atlas/register>.

        Using a managed MongoDB with Autogen brings significant benefits:
        1. It's fully managed, which means local installation is not required.
        2. It's cloud-agnostic, as it's available on multiple platforms including AWS, Azure, and GCP. 
        3. It offers enterprise-level vector storage, making it suitable for production environments.

        """
        mongo_url = "mongodb+srv://your_login:your_password@your_cluster?retryWrites=true&w=majority"
        client = pymongo.MongoClient(mongo_url)
        db = client["your_database"]
        collection = db["your_vector_collection"]
        return collection

    def find_similar_documents(self, embedding):
        """
        Find similar documents in MongoDB based on the provided embedding.
        Prerequisites: 
        1. Ensure that your data with the embedding is already stored in MongoDB.
        2. Have a vector index defined in MongoDB. For guidance on how to create your vector index, you can refer to the following link: <https://www.mongodb.com/docs/atlas/atlas-search/field-types/knn-vector/>.
        3. Understand the details of a Vector Query, such as what 'numCandidates' and 'limit' signify. For more information on this, please consult: <https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-stage/>.
        This will allow you to effectively find similar documents based on your specific embedding.
        """
        collection = self.connect_mongodb()
        documents = list(collection.aggregate([

            {
                "$vectorSearch": {
                    "index": "<your_vector_index>",
                    "path": "<your_embedding_field-to-search>",
                    "queryVector": embedding,
                    "numCandidates": 50,
                    "limit": 10
                }
            },
            {"$project": {"_id": 1, "text_chunks": 1}}
        ]))
        return documents


# Instantiate the Assistant Agent with provided configuration
assistant = RetrieveAssistantAgent(
    name="assistant",
    system_message="You are a helpful assistant.",
    llm_config=config_list,
)

# Instantiate the User Proxy Agent with MongoDB functionality
ragproxyagent = MongoDBRetrieveUserProxyAgent(
    name="MongoDB_RAG_Agent",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=2,
    retrieve_config={
        "task": "qa",
    },
)

# Reset the assistant and retrieve documents for a specific problem
assistant.reset()
ragproxyagent.initiate_chat(
    assistant, problem="What is the average price of client A's expense based on his purchase history provided?"
)
