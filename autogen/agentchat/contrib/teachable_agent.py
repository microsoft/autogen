from autogen import oai
from autogen.agentchat.agent import Agent
from autogen.agentchat.assistant_agent import ConversableAgent
from autogen.agentchat.contrib.text_analyzer import TextAnalyzer
from autogen.agentchat.contrib.analysis_agent import AnalysisAgent
from typing import Callable, Dict, Optional, Union, List, Tuple, Any
import chromadb
from chromadb.config import Settings


class TeachableAgent(ConversableAgent):
    """(Ongoing research) Teachable Assistant agent, using a vector database as a memory store.
    """
    def __init__(
        self,
        name: str,
        system_message: Optional[str] = "You are a helpful AI assistant.",
        llm_config: Optional[Union[Dict, bool]] = None,
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Optional[str] = "NEVER",
        code_execution_config: Optional[Union[Dict, bool]] = False,
        **kwargs,
    ):
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

        self.verbosity   = 0  # 1 to print DB operations, 2 to add caller details.
        self.db_method   = 1  # 0=none, 1=Both tasks & facts
        self.prepopulate = 1  # 1 to prepopulate the DB with a set of input-output pairs.
        self.use_cache   = False  # 1 to skip LLM calls made previously by relying on cached responses.
        self.use_analyzer_agent = 1  # 1 to use the new analysis agent, 0 to use the old text analyzer.

        if self.use_analyzer_agent:
            self.analyzer = AnalysisAgent("analyzer", llm_config=llm_config)
        else:
            self.text_analyzer = TextAnalyzer(self.use_cache)

        if self.db_method > 0:
            self.memo_store = MemoStore(self.verbosity)
            self.memo_store.prepopulate()
            self.user_comments = []  # Stores user comments until the end of the chat.

    def delete_db(self):
        self.memo_store.db_client.reset()

    def _generate_teachable_assistant_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        if self.use_analyzer_agent and (sender == self.analyzer):
            # This is a response from the text analyzer. Don't reply to it.
            return True, None

        # Are the following tests necessary?
        llm_config = self.llm_config if config is None else config
        if llm_config is False:
            return False, None
        if messages is None:
            messages = self._oai_messages[sender]

        # messages contains the previous chat history, excluding the system message.

        # Get the last user message.
        user_text = messages[-1]['content']

        # To let an interactive user test memory, clear the chat history if the user says "new chat".
        if user_text == 'new chat':
            self.clear_history()
            print('\n\033[92m<STARTING A NEW CHAT WITH EMPTY CONTEXT>\033[0m  ')
            self.learn_from_recent_user_comments()
            return True, 'New chat started.'

        if self.db_method > 0:
            # This is a normal user turn. Keep track of it for potential storage later.
            self.user_comments.append(user_text)

            if self.memo_store.num_memos > 0:
                # Consider whether to retrieve something from the DB.
                new_user_text = self.consider_memo_retrieval(user_text, llm_config)
                if new_user_text != user_text:
                    # Make a copy of the message list, and replace the last user message with the new one.
                    messages = messages.copy()
                    messages[-1]['content'] = new_user_text

        ctxt = messages[-1].pop("context", None)  # This peels off any "context" message from the list.
        msgs = self._oai_system_message + messages
        response = oai.ChatCompletion.create(context=ctxt, messages=msgs, use_cache=self.use_cache, **llm_config)
        response_text = oai.ChatCompletion.extract_text_or_function_call(response)[0]

        return True, response_text

    def learn_from_recent_user_comments(self):
        if self.db_method > 0:
            # Look at each user turn.
            if len(self.user_comments) > 0:
                for comment in self.user_comments:
                    # Consider whether to store something from this user turn in the DB.
                    self.consider_memo_storage(comment, self.llm_config)
            self.user_comments = []

    def consider_memo_storage(self, comment, llm_config):
        # Check for a problem-solution pair.
        response = self.analyze(llm_config, comment,
            "Does the last user comment contain a task or problem to solve? Answer with just one word, yes or no.")
        if 'yes' in response.lower():
            # Can we extract advice?
            advice = self.analyze(llm_config, comment,
                "Copy any advice from the last user comment that may be useful for a similar but different task in the future. But if no advice is present, just respond with \'none\'.")
            if 'none' not in advice.lower():
                # Yes. Extract the task.
                task = self.analyze(llm_config, comment,
                    "Copy just the task from the last user comment, then stop. Don't solve it, and don't include any advice.")
                # Generalize the task.
                general_task = self.analyze(llm_config, task,
                    "Summarize very briefly, in general terms, the type of task described in the last user comment. Leave out details that might not appear in a similar problem.")
                # Add the task-advice (problem-solution) pair to the vector DB.
                if self.verbosity >= 1:
                    print("\n\033[92m<FOUND TASK-ADVICE PAIR>\033[0m  ")
                self.memo_store.add_input_output_pair(general_task, advice)
            return

        # Check for a simple question.
        response = self.analyze(llm_config, comment,
            "Does the last user comment contain a simple question? Answer with just one word, yes or no.")
        if 'yes' in response.lower():
            # Ignore it.
            return

        # Check for information to be learned.
        response = self.analyze(llm_config, comment,
            "Does the last user comment contain information that might be useful later? Answer with just one word, yes or no.")
        if 'yes' in response.lower():
            # Yes. What question would this information answer?
            question = self.analyze(llm_config, comment,
                "Imagine that the user forgot this information in their last comment. How would they ask you for this information? Include no other text in your response.")
            # Extract the information.
            answer = self.analyze(llm_config, comment,
                "Copy the information from the last user comment that may be useful later.")
            # Add the question-answer pair to the vector DB.
            if self.verbosity >= 1:
                print("\n\033[92m<FOUND QUESTION-ANSWER PAIR>\033[0m  ")
            self.memo_store.add_input_output_pair(question, answer)

    def consider_memo_retrieval(self, comment, llm_config):
        # Check for a question or task.
        response = self.analyze(llm_config, comment,
            "Does the last user comment contain a question, task, or problem to solve? Answer with just one word, yes or no.")
        if 'yes' in response.lower():
            # Distinguish between a question and a task.
            response = self.analyze(llm_config, comment,
                "Would the last user comment be best described as a simple question question, or a complex task? Answer with just one word, question or task.")
            if 'question' in response.lower():
                # Retrieve the answer.
                uid, info = self.memo_store.get_nearest_memo(comment)
                answer = self.memo_store.info_dict[uid]
                info = "(Here is some information that might help answer the question:\n" + answer + ")"
                if self.verbosity >= 1:
                    print('\n' + info)
                user_text = comment + '\n' + info
                return user_text
            elif 'task' in response.lower():
                # Extract the task.
                task = self.analyze(llm_config, comment,
                    "Copy just the task from the last user comment, then stop. Don't solve it, and don't include any advice.")
                # Generalize the task.
                general_task = self.analyze(llm_config, task,
                    "Summarize very briefly, in general terms, the type of task described in the last user comment. Leave out details that might not appear in a similar problem.")
                # Retrieve the advice.
                uid, info = self.memo_store.get_nearest_memo(general_task)
                advice = self.memo_store.info_dict[uid]
                info = "(Here is some advice that might help:\n" + advice + ")"
                if self.verbosity >= 1:
                    print('\n' + info)
                user_text = comment + '\n' + info
                return user_text

        # For anything else, just return the user comment.
        return comment

    def analyze(self, llm_config, text_to_analyze, analysis_instructions):
        if self.use_analyzer_agent:
            message_text = '\n'.join([text_to_analyze, analysis_instructions])
            self.initiate_chat(recipient=self.analyzer, message=message_text)
            response_text = self.last_message(self.analyzer)["content"]
        else:
            response_text = self.text_analyzer.analyze(llm_config, text_to_analyze, analysis_instructions)
        return response_text


class MemoStore():
    def __init__(self, verbosity):
        self.verbosity = verbosity
        # TODO: Expose an option to persist the DB to a file on disk.
        self.db_client = chromadb.Client(Settings(anonymized_telemetry=False, allow_reset=True))  # In-memory by default.
        self.vec_db = self.db_client.create_collection("memos")  # The collection is the DB.
        self.next_uid = 0  # Unique ID for each memo. Also serves as a count of total memos added.
        self.num_memos = 0
        self.info_dict = {}  # Maps a memo uid to information like answers or advice.

    def add_memo(self, text):
        self.next_uid += 1
        self.num_memos += 1
        self.vec_db.add(documents=[text], ids=[str(self.next_uid)])
        if self.verbosity >= 1:
            print("\n\033[92m<USER COMMENT ADDED TO VECTOR DATABASE:  {}>\033[0m  ".format(text))

    def add_input_output_pair(self, input_text, output_text):
        self.next_uid += 1
        self.num_memos += 1
        self.vec_db.add(documents=[input_text], ids=[str(self.next_uid)])
        self.info_dict[str(self.next_uid)] = output_text
        if self.verbosity >= 1:
            print("\n\033[92m<INPUT-OUTPUT PAIR ADDED TO VECTOR DATABASE:\nINPUT\n{}\nOUTPUT\n{}>\033[0m  ".format(input_text, output_text))

    def get_nearest_memo(self, query_text):
        results = self.vec_db.query(query_texts=[query_text], n_results=1)
        return results['ids'][0][0], results['documents'][0][0]

    def prepopulate(self):
        # Add some random examples to the vector DB, just to make retrieval less trivial.
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
