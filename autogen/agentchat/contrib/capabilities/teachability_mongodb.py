import os
from typing import Dict, Optional, Union

from openai import embeddings
import pymongo

from autogen.agentchat.assistant_agent import ConversableAgent
from autogen.agentchat.contrib.capabilities.agent_capability import AgentCapability
from autogen.agentchat.contrib.text_analyzer_agent import TextAnalyzerAgent

from autogen.formatting_utils import colored


class Teachability_MongoDBvCore(AgentCapability):
    """
    Teachability uses a vector database to give an agent the ability to remember user teachings,
    where the user is any caller (human or not) sending messages to the teachable agent.
    Teachability is designed to be composable with other agent capabilities.
    To make any conversable agent teachable, instantiate both the agent and the Teachability class,
    then pass the agent to teachability.add_to_agent(agent).
    Note that teachable agents in a group chat must be given unique path_to_db_dir values.
    ?Each agent gets its own database?

    When adding Teachability to an agent, the following are modified:
    - The agent's system message is appended with a note about the agent's new ability. Ok
    - A hook is added to the agent's `process_last_received_message` hookable method, Ok
    and the hook potentially modifies the last of the received messages to include earlier teachings related to the message.
    Added teachings do not propagate into the stored message history. Ok
    If new user teachings are detected, they are added to new memos in the vector database. Ok.

    This class uses a MongoDB vCore database to store memos. When you instantiage this class,
    you must provide a connection string to the MongoDB vCore database.
    Also, this class will create a collection called 'memo_pairs' in the 'memos' database by default.
    It will also create a vector search index named 'memo_pairs_vector_index' in the 'memo_pairs' collection,
    this is necessary for the vector search to work.

    You can change this behavior when initializing the class by providing the desired database name and collection name.
    You can even have a different database or collection for each agent (recommended).
    """

    def __init__(
        self,
        verbosity: Optional[int] = 0,
        reset_db: Optional[bool] = False,
        connection_string: str = "your Mongodb vCore connection string here",
        mongodb_database_name: Optional[str] = "memos",
        mongodb_collection_name: Optional[str] = "memo_pairs",
        recall_threshold: Optional[float] = 1.5,
        max_num_retrievals: Optional[int] = 10,
        llm_config: Optional[Union[Dict, bool]] = None,
    ):
        """
        Args:
            verbosity (Optional, int): # 0 (default) for basic info, 1 to add memory operations, 2 for analyzer messages, 3 for memo lists.
            reset_db (Optional, bool): True to clear the DB before starting. Default False.
            connection_string (str): The connection string to the MongoDB vCore database.
            recall_threshold (Optional, float): The maximum distance for retrieved memos, where 0.0 is exact match. Default 1.5. Larger values allow more (but less relevant) memos to be recalled.
            max_num_retrievals (Optional, int): The maximum number of memos to retrieve from the DB. Default 10.
            llm_config (dict or False): llm inference configuration passed to TextAnalyzerAgent.
                If None, TextAnalyzerAgent uses llm_config from the teachable agent.
        """
        self.verbosity = verbosity
        self.connection_string = connection_string
        self.mongodb_database_name = mongodb_database_name
        self.mongodb_collection_name = mongodb_collection_name
        self.recall_threshold = recall_threshold
        self.max_num_retrievals = max_num_retrievals
        self.llm_config = llm_config

        self.analyzer = TextAnalyzerAgent(llm_config=self.llm_config)
        self.teachable_agent = None

        # Create the memo store.
        self.memo_store = MongoDBvCoreMemoStore(
            verbosity=self.verbosity,
            reset=False,
            connection_string=self.connection_string,
            mongodb_database_name=mongodb_database_name,
            mongodb_collection_name=mongodb_collection_name,
        )

    def add_to_agent(self, agent: ConversableAgent):
        """Adds teachability to the given agent."""
        self.teachable_agent = agent

        # Register a hook for processing the last message.
        agent.register_hook(
            hookable_method="process_last_received_message",
            hook=self.process_last_received_message,
        )

        # Was an llm_config passed to the constructor?
        if self.llm_config is None:
            # No. Use the agent's llm_config.
            self.llm_config = agent.llm_config
        assert self.llm_config, "Teachability requires a valid llm_config."

        # Create the analyzer agent.
        self.analyzer = TextAnalyzerAgent(llm_config=self.llm_config)

        # Append extra info to the system message.
        agent.update_system_message(
            agent.system_message
            + "\nYou've been given the special ability to remember user teachings from prior conversations."
        )

    def prepopulate_db(self):
        """Adds a few arbitrary memos to the DB."""
        self.memo_store.prepopulate()

    def process_last_received_message(self, text: Union[Dict, str]):
        """
        Appends any relevant memos to the message text, and stores any apparent teachings in new memos.
        Uses TextAnalyzerAgent to make decisions about memo storage and retrieval.
        """

        # Try to retrieve relevant memos from the DB.
        expanded_text = self._consider_memo_retrieval(text)

        # Try to store any user teachings in new memos to be used in the future.
        self._consider_memo_storage(text)

        # Return the (possibly) expanded message text.
        return expanded_text

    def _consider_memo_storage(self, comment: Union[Dict, str]):
        """Decides whether to store something from one user comment in the DB."""
        memo_added = False

        # Check for a problem-solution pair.
        response = self._analyze(
            comment,
            "Does any part of the TEXT ask the agent to perform a task or solve a problem? Answer with just one word, yes or no.",
        )
        if "yes" in response.lower():
            # Can we extract advice?
            advice = self._analyze(
                comment,
                "Briefly copy any advice from the TEXT that may be useful for a similar but different task in the future. But if no advice is present, just respond with 'none'.",
            )
            if "none" not in advice.lower():
                # Yes. Extract the task.
                task = self._analyze(
                    comment,
                    "Briefly copy just the task from the TEXT, then stop. Don't solve it, and don't include any advice.",
                )
                # Generalize the task.
                general_task = self._analyze(
                    task,
                    "Summarize very briefly, in general terms, the type of task described in the TEXT. Leave out details that might not appear in a similar problem.",
                )
                # Add the task-advice (problem-solution) pair to the vector DB.
                if self.verbosity >= 1:
                    print(colored("\nREMEMBER THIS TASK-ADVICE PAIR", "light_yellow"))

                # upload to mongodb
                self.memo_store.add_input_output_pair(general_task, advice)
                memo_added = True

        # Check for information to be learned.
        response = self._analyze(
            comment,
            "Does the TEXT contain information that could be committed to memory? Answer with just one word, yes or no.",
        )
        if "yes" in response.lower():
            # Yes. What question would this information answer?
            question = self._analyze(
                comment,
                "Imagine that the user forgot this information in the TEXT. How would they ask you for this information? Include no other text in your response.",
            )
            # Extract the information.
            answer = self._analyze(
                comment,
                "Copy the information from the TEXT that should be committed to memory. Add no explanation.",
            )
            # Add the question-answer pair to the vector DB.
            if self.verbosity >= 1:
                print(colored("\nREMEMBER THIS QUESTION-ANSWER PAIR", "light_yellow"))
            # upload to mongodb
            self.memo_store.add_input_output_pair(question, answer)
            memo_added = True

    def _consider_memo_retrieval(self, comment: Union[Dict, str]):
        """Decides whether to retrieve memos from the DB, and add them to the chat context."""

        # First, use the comment directly as the lookup key.
        if self.verbosity >= 1:
            print(
                colored(
                    "\nLOOK FOR RELEVANT MEMOS, AS QUESTION-ANSWER PAIRS",
                    "light_yellow",
                )
            )
        memo_list = self._retrieve_relevant_memos(
            comment
        )  # Retrieve memos relevant to the agent's last message, raw text

        # Next, if the comment involves a task, then extract and generalize the task before using it as the lookup key.
        response = self._analyze(
            comment,
            "Does any part of the TEXT ask the agent to perform a task or solve a problem? Answer with just one word, yes or no.",
        )
        if "yes" in response.lower():
            if self.verbosity >= 1:
                print(
                    colored(
                        "\nLOOK FOR RELEVANT MEMOS, AS TASK-ADVICE PAIRS",
                        "light_yellow",
                    )
                )
            # Extract the task.
            task = self._analyze(
                comment,
                "Copy just the task from the TEXT, then stop. Don't solve it, and don't include any advice.",
            )  # you can also store stuff as task-advice pairs
            # Generalize the task.
            general_task = self._analyze(
                task,
                "Summarize very briefly, in general terms, the type of task described in the TEXT. Leave out details that might not appear in a similar problem.",
            )
            # Ok use AI to find out what the general task is, then retrieve memos where the question/key
            # is close to that task
            # Append any relevant memos.
            memo_list.extend(self._retrieve_relevant_memos(general_task))

        # De-duplicate the memo list.
        memo_list = list(set(memo_list))

        # Append the memos to the text of the last message.
        return comment + self._concatenate_memo_texts(memo_list)

    def _retrieve_relevant_memos(self, input_text: str) -> list:
        """Returns semantically related memos from the DB."""
        memo_list = self.memo_store.get_related_memos(
            input_text,
            n_results=self.max_num_retrievals,
            threshold=self.recall_threshold,
        )

        if self.verbosity >= 1:
            # Was anything retrieved?
            if len(memo_list) == 0:
                # No. Look at the closest memo.
                print(
                    colored(
                        "\nTHE CLOSEST MEMO IS BEYOND THE THRESHOLD:", "light_yellow"
                    )
                )
                self.memo_store.get_nearest_memo(input_text)
                print()  # Print a blank line. The memo details were printed by get_nearest_memo().

        # Create a list of just the memo output_text strings.
        memo_list = [memo[1] for memo in memo_list]
        return memo_list

    def _concatenate_memo_texts(self, memo_list: list) -> str:
        """Concatenates the memo texts into a single string for inclusion in the chat context."""
        memo_texts = ""
        if len(memo_list) > 0:
            info = "\n# Memories that might help\n"
            for memo in memo_list:
                info = info + "- " + memo + "\n"
            if self.verbosity >= 1:
                print(
                    colored(
                        "\nMEMOS APPENDED TO LAST MESSAGE...\n" + info + "\n",
                        "light_yellow",
                    )
                )
            memo_texts = memo_texts + "\n" + info
        return memo_texts

    def _analyze(
        self, text_to_analyze: Union[Dict, str], analysis_instructions: Union[Dict, str]
    ):
        """Asks TextAnalyzerAgent to analyze the given text according to specific instructions."""
        self.analyzer.reset()  # Clear the analyzer's list of messages.
        self.teachable_agent.send(
            recipient=self.analyzer,
            message=text_to_analyze,
            request_reply=False,
            silent=(self.verbosity < 2),
        )  # Put the message in the analyzer's list.
        self.teachable_agent.send(
            recipient=self.analyzer,
            message=analysis_instructions,
            request_reply=True,
            silent=(self.verbosity < 2),
        )  # Request the reply.
        return self.teachable_agent.last_message(self.analyzer)["content"]


class MongoDBvCoreMemoStore:
    """
    Provides memory storage and retrieval for a teachable agent, using an Azure CosmosDB for MongoDB vCore vector database.
    Each DB entry (called a memo) is a pair of strings: an input text and an output text.
    The input text might be a question, or a task to perform.
    The output text might be an answer to the question, or advice on how to perform the task.
    """

    def __init__(
        self,
        verbosity: Optional[int] = 3,
        reset: Optional[bool] = False,
        connection_string: str = "your MongoDB vCore connection string here",
        mongodb_database_name="memos",
        mongodb_collection_name="memo_pairs",
    ):
        """
        Args:
            - verbosity (Optional, int): 1 to print memory operations, 0 to omit them. 3+ to print memo lists.
            - reset (Optional, bool): True to clear the DB before starting. Default False.
            - connection_string (str): The connection string to the MongoDB database.
        """
        self.verbosity = verbosity
        self.connection_string = connection_string
        self.mongodb_database_name = mongodb_database_name
        self.mongodb_collection_name = mongodb_collection_name

        self.mongodb_client = pymongo.MongoClient(connection_string)
        self.vector_db = self.mongodb_client[self.mongodb_database_name]

        # create the memos database unless it already exists
        self.vector_collection = self.vector_db[self.mongodb_collection_name]

        # Clear the DB if requested.
        if reset:
            self.reset_db()

        # self.prepopulate()
        self._create_vector_index_if_not_exists()

    # Do I need to recall memories from mongodb and then save them in the dict for the rest of the
    # conversation?

    def reset_db(self):
        """Forces immediate deletion of the DB's contents, in memory and on disk."""
        print(colored("\nCLEARING MEMORY", "light_green"))

        # Drop the collection

    def _create_vector_index_if_not_exists(self):
        """Creates a vector index in the DB if it doesn't already exist."""

        current_indexes = self.vector_collection.list_indexes()
        for index in current_indexes:
            if f"{self.mongodb_collection_name}_index" in str(index):
                print("Index already created! We are good to go.")
                return "Index already created! We are good to go."

        create_index = self.vector_db.command(
            {
                "createIndexes": self.mongodb_collection_name,
                "indexes": [
                    {
                        "name": f"{self.mongodb_collection_name}_index",
                        "key": {"embeddings": "cosmosSearch"},
                        "cosmosSearchOptions": {
                            "kind": "vector-ivf",
                            "numLists": 800,
                            "similarity": "COS",
                            "dimensions": 1536,
                        },
                    }
                ],
            }
        )

        print(f"Index created! {create_index}")
        return create_index

    def embed_text(self, text):
        from openai import AzureOpenAI

        client = AzureOpenAI(
            api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
            api_version="2024-03-01-preview",
            azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
        )
        print("Embedding text...")
        if len(text > 8196):
            text = text[:8196]
            print(
                "Text truncated to 8196 characters, because the embedding model can't handle more than that."
            )
        print(text)
        response = client.embeddings.create(
            input=text, model="text-embedding-3-small", dimensions=1536
        )
        embeddings = response.data[0].embedding
        return embeddings

    def add_input_output_pair(self, input_text: str, output_text: str):
        """Adds an input-output pair to the vector DB."""
        # Insert the input-output pair into the MongoDB collection

        embeddings = self.embed_text(input_text)

        response_from_db = self.vector_collection.insert_one(
            {
                "input": input_text,
                "output": output_text,
                "embeddings": embeddings,
            }
        )
        print(
            "\nINPUT-OUTPUT PAIR ADDED TO VECTOR DATABASE:\n  INPUT\n    {}\n  OUTPUT\n    {}\n".format(
                input_text, output_text
            )
        )

        return response_from_db

    def get_nearest_memo(self, query_text: str):
        """Retrieves the nearest memo to the given query text."""
        # can you retrieve the distance/similarity too for the threshold?
        embedded_query = self.embed_text(query_text)
        # search for the related memos, with n results
        results = self.vector_collection.aggregate(
            [
                {
                    "$search": {
                        "cosmosSearch": {
                            "vector": embedded_query,
                            "path": "embeddings",
                            "k": 1,
                        },
                        "returnStoredSource": True,
                    }
                }
            ]
        )
        results_list = list(results)
        print(results_list)
        input_text = results_list[0]["input"]
        output_text = results_list[0]["output"]

        if self.verbosity >= 1:
            print(
                colored(
                    "\nINPUT-OUTPUT PAIR RETRIEVED FROM VECTOR DATABASE:\n  INPUT1\n    {}\n  OUTPUT\n    {}\n  DISTANCE\n    {}".format(
                        input_text, output_text
                    ),
                    "light_yellow",
                )
            )
        return input_text, output_text

    def get_related_memos(
        self, query_text: str, n_results: int, threshold: Union[int, float]
    ):
        """Retrieves memos that are related to the given query text within the specified distance threshold."""
        # embed the query
        embedded_query = self.embed_text(query_text)
        # search for the related memos, with n results
        results = self.vector_collection.aggregate(
            [
                {
                    "$search": {
                        "cosmosSearch": {
                            "vector": embedded_query,
                            "path": "embeddings",
                            "k": 10,
                        },
                        "returnStoredSource": True,
                    }
                }
            ]
        )

        related_memos = []
        results_list = list(results)
        for i in range(len(results_list)):
            if i >= n_results:
                break
            # Uncomment if we get the distance returned from the vector seatch
            # if distance < threshold:
            #     if self.verbosity >= 1:
            #         print(
            #             colored(
            #                 "\nINPUT-OUTPUT PAIR RETRIEVED FROM VECTOR DATABASE:\n  INPUT1\n    {}\n  OUTPUT\n    {}\n  DISTANCE\n    {}".format(
            #                     input_text, output_text, distance
            #                 ),
            #                 "light_yellow",
            #             )
            #         )
            # memos.append((input_text, output_text, distance))

            input_text = results_list[i]["input"]
            output_text = results_list[i]["output"]
            related_memos.append((input_text, output_text))

        return related_memos

    def prepopulate(self):
        """Adds a few arbitrary examples to the vector DB, just to make retrieval less trivial."""
        if self.verbosity >= 1:
            print(colored("\nPREPOPULATING MEMORY", "light_green"))
        examples = []
        examples.append(
            {
                "input": "When I say papers I mean research papers, which are typically pdfs.",
                "output": "yes",
            }
        )
        examples.append(
            {
                "input": "Tell gpt the output should be written in markdown.",
                "output": "OK",
            }
        )

        for example in examples:
            self.add_input_output_pair(example["input"], example["output"])
