from autogen import oai
from autogen.agentchat.agent import Agent
from autogen.agentchat.assistant_agent import ConversableAgent
from autogen.agentchat.contrib.analysis_agent import AnalysisAgent
from typing import Callable, Dict, Optional, Union, List, Tuple, Any
import chromadb
from chromadb.config import Settings


try:
    from termcolor import colored
except ImportError:
    def colored(x, *args, **kwargs):
        return x


class TeachableAgent(ConversableAgent):
    """(Ongoing research) Teachable Assistant agent, using a vector database as a memory store.
    """
    def __init__(
        self,
        name="Assistant",  # default set to Assistant
        system_message: Optional[str] = "You are a helpful AI assistant.",
        llm_config: Optional[Union[Dict, bool]] = None,
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Optional[str] = "NEVER",
        code_execution_config: Optional[Union[Dict, bool]] = False,
        teach_config: Optional[Dict] = None,  # config for the TeachableAgent
        **kwargs,
    ):
        """
        Args:
            name (str): name of the agent. Default "Assistant".
            human_input_mode (str): NEVER ask for human input for this agent.
            teach_config (dict or None): config for the TeachableAgent.
                To use default config, set to None. Otherwise, set to a dictionary with any of the following keys:
                - verbosity (Optional, int): 1 to print DB operations, 2 to add caller details. Default 0.
                - prepopulate (Optional, int): 1 to prepopulate the DB with a set of input-output pairs. Default 1.
                - use_cache (Optional, bool): True to skip LLM calls made previously by relying on cached responses. Default False.
                - recall_threshold (Optional, float): The distance threshold for retrieving memos from the DB. Default 1.5.
            **kwargs (dict): other kwargs in [ConversableAgent](../conversable_agent#__init__).
        """
        super().__init__(
            name,
            system_message,
            is_termination_msg,
            max_consecutive_auto_reply,
            human_input_mode,
            code_execution_config=code_execution_config,
            llm_config=llm_config,
            **kwargs,
        )
        self.register_reply(Agent, TeachableAgent._generate_teachable_assistant_reply)

        self._teach_config = {} if teach_config is None else teach_config
        self.verbosity = self._teach_config.get("verbosity", 0)
        self.prepopulate = self._teach_config.get("prepopulate", 1)
        self.use_cache = self._teach_config.get("use_cache", False)
        self.recall_threshold = self._teach_config.get("recall_threshold", 1.5)

        self.analyzer = AnalysisAgent("analyzer", llm_config=llm_config)

        self.memo_store = MemoStore(self.verbosity)
        self.memo_store.prepopulate()
        self.user_comments = []  # Stores user comments until the end of each chat.

    def delete_db(self):
        self.memo_store.db_client.reset()

    def _generate_teachable_assistant_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,  # Persistent state.
    ) -> Tuple[bool, Union[str, Dict, None]]:
        """
        Generates a reply to the last user message, after querying the memo store for relevant information.
        Uses self.analyzer to make decisions about memo storage and retrieval.
        """
        if self.llm_config is False:
            return False, None  # Return if no LLM was provided.
        if messages is None:
            messages = self._oai_messages[sender]  # In case of a direct call.

        # Get the last user message.
        user_text = messages[-1]['content']

        # To help an interactive user test memory, clear the chat history if the user says "new chat".
        if user_text == 'new chat':
            self.clear_history()
            self.learn_from_recent_user_comments()
            print(colored("\nSTARTING A NEW CHAT WITH EMPTY CONTEXT", 'light_cyan'))
            return True, 'New chat started.'

        # This is a normal user turn. Keep track of it for potential storage later.
        self.user_comments.append(user_text)

        if self.memo_store.num_memos > 0:
            # Consider whether to retrieve something from the DB.
            new_user_text = self.consider_memo_retrieval(user_text)
            if new_user_text != user_text:
                # Make a copy of the message list, and replace the last user message with the new one.
                messages = messages.copy()
                messages[-1]['content'] = new_user_text

        ctxt = messages[-1].pop("context", None)  # This peels off any "context" message from the list.
        msgs = self._oai_system_message + messages
        response = oai.ChatCompletion.create(context=ctxt, messages=msgs, use_cache=self.use_cache, **self.llm_config)
        response_text = oai.ChatCompletion.extract_text_or_function_call(response)[0]

        return True, response_text

    def learn_from_recent_user_comments(self):
        print(colored("\nREVIEW CHAT FOR ITEMS TO REMEMBER", 'light_cyan'))
        # Look at each user turn.
        if len(self.user_comments) > 0:
            for comment in self.user_comments:
                # Consider whether to store something from this user turn in the DB.
                self.consider_memo_storage(comment)
        self.user_comments = []

    def consider_memo_storage(self, comment):
        """Decides whether to store something from this user turn in the DB."""
        # Check for a problem-solution pair.
        response = self.analyze(comment,
            "Does the TEXT contain a task or problem to solve? Answer with just one word, yes or no.")
        if 'yes' in response.lower():
            # Can we extract advice?
            advice = self.analyze(comment,
                "Briefly copy any advice from the TEXT that may be useful for a similar but different task in the future. But if no advice is present, just respond with \'none\'.")
            if 'none' not in advice.lower():
                # Yes. Extract the task.
                task = self.analyze(comment,
                    "Briefly copy just the task from the TEXT, then stop. Don't solve it, and don't include any advice.")
                # Generalize the task.
                general_task = self.analyze(task,
                    "Summarize very briefly, in general terms, the type of task described in the TEXT. Leave out details that might not appear in a similar problem.")
                # Add the task-advice (problem-solution) pair to the vector DB.
                if self.verbosity >= 1:
                    print(colored("\nREMEMBER THIS TASK-ADVICE PAIR", 'light_yellow'))
                self.memo_store.add_input_output_pair(general_task, advice)

        # Check for information to be learned.
        response = self.analyze(comment,
            "Does the TEXT contain information that might be useful later? Answer with just one word, yes or no.")
        if 'yes' in response.lower():
            # Yes. What question would this information answer?
            question = self.analyze(comment,
                "Imagine that the user forgot this information in the TEXT. How would they ask you for this information? Include no other text in your response.")
            # Extract the information.
            answer = self.analyze(comment,
                "Briefly copy the information from the TEXT that may be useful later.")
            # Add the question-answer pair to the vector DB.
            if self.verbosity >= 1:
                print(colored("\nREMEMBER THIS QUESTION-ANSWER PAIR", 'light_yellow'))
            self.memo_store.add_input_output_pair(question, answer)

    def consider_memo_retrieval(self, comment):
        """Decides whether to retrieve something from the DB."""

        # First, use the user comment directly as the lookup key.
        if self.verbosity >= 1:
            print(colored('\nLOOK FOR RELEVANT MEMOS, AS QUESTION-ANSWER PAIRS', 'light_yellow'))
        memo_list = self.retrieve_relevant_memos(comment)

        # Next, if the comment involves a task, then extract and generalize the task before using it as the lookup key.
        response = self.analyze(comment,
            "Does the TEXT contain a task or problem to solve? Answer with just one word, yes or no.")
        if 'yes' in response.lower():
            # Extract the task.
            task = self.analyze(comment,
                "Copy just the task from the TEXT, then stop. Don't solve it, and don't include any advice.")
            # Generalize the task.
            general_task = self.analyze(task,
                "Summarize very briefly, in general terms, the type of task described in the TEXT. Leave out details that might not appear in a similar problem.")
            # Append any relevant memos.
            if self.verbosity >= 1:
                print(colored('\nLOOK FOR RELEVANT MEMOS, AS TASK-ADVICE PAIRS', 'light_yellow'))
            memo_list.extend(self.retrieve_relevant_memos(general_task))

        # De-duplicate the memo list.
        memo_list = list(set(memo_list))

        # Append the memos to the last user message.
        return comment + self.concatenate_memo_texts(memo_list)

    def retrieve_relevant_memos(self, input_text):
        memo_list = self.memo_store.get_related_memos(input_text, threshold=self.recall_threshold)

        if self.verbosity >= 1:
            # Was anything retrieved?
            if len(memo_list) == 0:
                # No. Look at the closest memo.
                print(colored('\nTHE CLOSEST MEMO IS BEYOND THE THRESHOLD...', 'light_yellow'))
                memo = self.memo_store.get_nearest_memo(input_text)
                print()  # Print a blank line. The memo details were printed by get_nearest_memo().

        # Create a list of just the memo output_text strings.
        memo_list = [memo[1] for memo in memo_list]
        return memo_list

    def concatenate_memo_texts(self, memo_list):
        memo_texts = ''
        for memo in memo_list:
            info = "(Here is some information that might help:\n" + memo + ")"
            if self.verbosity >= 1:
                print(colored('\nMEMO APPENDED TO LAST USER MESSAGE...\n' + info + '\n', 'light_yellow'))
            memo_texts = memo_texts + '\n' + info
        return memo_texts

    def analyze(self, text_to_analyze, analysis_instructions):
        """Sends the text to analyze and the analysis instructions to the analyzer."""
        self.analyzer.reset()  # Clear the analyzer's list of messages.
        self.send(recipient=self.analyzer, message=text_to_analyze, request_reply=False)  # Put the message in the analyzer's list.
        self.send(recipient=self.analyzer, message=analysis_instructions, request_reply=True)  # Request the reply.
        return self.last_message(self.analyzer)["content"]


class MemoStore():
    def __init__(self, verbosity):
        self.verbosity = verbosity
        # TODO: Expose an option to persist the DB to a file on disk.
        self.db_client = chromadb.Client(Settings(anonymized_telemetry=False, allow_reset=True))  # In-memory by default.
        self.vec_db = self.db_client.create_collection("memos")  # The collection is the DB.
        self.next_uid = 0  # Unique ID for each memo. Also serves as a count of total memos added.
        self.num_memos = 0
        self.info_dict = {}  # Maps a memo uid to information like answers or advice.

    def add_input_output_pair(self, input_text, output_text):
        """ Adds an input-output pair to the vector DB. """
        self.next_uid += 1
        self.num_memos += 1
        self.vec_db.add(documents=[input_text], ids=[str(self.next_uid)])
        self.info_dict[str(self.next_uid)] = output_text
        if self.verbosity >= 1:
            print(colored("\nINPUT-OUTPUT PAIR ADDED TO VECTOR DATABASE:\n  INPUT\n    {}\n  OUTPUT\n    {}".format(
                input_text, output_text), 'light_green'))

    def get_nearest_memo(self, query_text):
        """ Retrieves the nearest memo to the given query text. """
        results = self.vec_db.query(query_texts=[query_text], n_results=1)
        uid, input_text, distance = results['ids'][0][0], results['documents'][0][0], results['distances'][0][0]
        output_text = self.info_dict[uid]
        if self.verbosity >= 1:
            print(colored("\nINPUT-OUTPUT PAIR RETRIEVED FROM VECTOR DATABASE:\n  INPUT\n    {}\n  OUTPUT\n    {}\n  DISTANCE\n    {}".format(
                input_text, output_text, distance), 'light_green'))
        return input_text, output_text, distance

    def get_related_memos(self, query_text, n_results=4, threshold=1.4):
        """ Retrieves memos that are related to the given query text with the threshold. """
        results = self.vec_db.query(query_texts=[query_text], n_results=n_results)
        memos = []
        num_results = len(results['ids'][0])
        for i in range(num_results):
            uid, input_text, distance = results['ids'][0][i], results['documents'][0][i], results['distances'][0][i]
            if distance < threshold:
                output_text = self.info_dict[uid]
                if self.verbosity >= 1:
                    print(colored(
                        "\nINPUT-OUTPUT PAIR RETRIEVED FROM VECTOR DATABASE:\n  INPUT\n    {}\n  OUTPUT\n    {}\n  DISTANCE\n    {}".format(
                            input_text, output_text, distance), 'light_green'))
                memos.append((input_text, output_text, distance))
        return memos

    def prepopulate(self):
        """ Adds arbitrary examples to the vector DB, just to make retrieval less trivial. """
        examples = []
        examples.append({'text': 'When I say papers I mean research papers, which are typically pdfs.', 'label': 'yes'})
        examples.append({'text': 'Please verify that each paper you listed actually uses langchain.', 'label': 'no'})
        examples.append({'text': 'Tell gpt the output should still be latex code.', 'label': 'no'})
        examples.append({'text': 'Hint: convert pdfs to text and then answer questions based on them.', 'label': 'yes'})
        examples.append({'text': 'To create a good PPT, include enough content to make it interesting.', 'label': 'yes'})
        examples.append({'text': 'No, for this case the columns should be aspects and the rows should be frameworks.', 'label': 'no'})
        examples.append({'text': 'When writing code, remember to include any libraries that are used.', 'label': 'yes'})
        examples.append({'text': 'Please summarize the papers by Eric Horvitz on bounded rationality.', 'label': 'no'})
        examples.append({'text': 'Compare the h-index of Daniel Weld and Oren Etzioni.', 'label': 'no'})
        examples.append({'text': 'Double check to be sure that the columns in a table correspond to what was asked for.', 'label': 'yes'})
        for example in examples:
            self.add_input_output_pair(example['text'], example['label'])
