import time
from typing import List, Union

from autogen_core import Image
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    SystemMessage,
    UserMessage,
)

from .utils._functions import UserContent
from .utils.page_logger import PageLogger


class Prompter:
    """
    Centralizes most of the Apprentice prompts sent to the model client.

    Args:
        client: The client to call the model.
        logger: An optional logger. If None, no logging will be performed.
    """

    def __init__(self, client: ChatCompletionClient, logger: PageLogger | None = None) -> None:
        if logger is None:
            logger = PageLogger()  # Nothing will be logged by this object.
        self.logger = logger

        self.client = client
        self.default_system_message_content = "You are a helpful assistant."
        self.time_spent_in_model_calls = 0.0
        self.num_model_calls = 0
        self.start_time = time.time()

        # Create the chat history
        self._chat_history: List[LLMMessage] = []

    async def call_model(
        self,
        summary: str,
        user_content: UserContent,
        system_message_content: str | None = None,
        keep_these_messages: bool = True,
    ) -> str:
        """
        Calls the model client with the given input and returns the response.
        """
        # Prepare the input message list
        if system_message_content is None:
            system_message_content = self.default_system_message_content
        system_message: LLMMessage
        if self.client.model_info["family"] == "o1":
            # No system message allowed, so pass it as the first user message.
            system_message = UserMessage(content=system_message_content, source="User")
        else:
            # System message allowed.
            system_message = SystemMessage(content=system_message_content)

        user_message = UserMessage(content=user_content, source="User")
        input_messages = [system_message] + self._chat_history + [user_message]

        # Double check the types of the input messages.
        for message in input_messages:
            for part in message.content:
                assert isinstance(part, str) or isinstance(part, Image), "Invalid message content type: {}".format(
                    type(part)
                )

        # Call the model
        start_time = time.time()
        response = await self.client.create(input_messages)
        assert isinstance(response, CreateResult)
        response_string = response.content
        assert isinstance(response_string, str)
        response_message = AssistantMessage(content=response_string, source="Assistant")
        assert isinstance(response_message, AssistantMessage)
        self.time_spent_in_model_calls += time.time() - start_time
        self.num_model_calls += 1

        # Log the model call
        self.logger.log_model_call(summary=summary, input_messages=input_messages, response=response)

        # Manage the chat history
        if keep_these_messages:
            self._chat_history.append(user_message)
            self._chat_history.append(response_message)

        # Return the response as a string for now
        return response_string

    def _clear_history(self) -> None:
        """
        Empties the message list containing the chat history.
        """
        self._chat_history = []

    async def learn_from_failure(
        self, task_description: str, memory_section: str, final_response: str, expected_answer: str, work_history: str
    ) -> str:
        """
        Tries to create an insight to help avoid the given failure in the future.
        """
        sys_message = """- You are a patient and thorough teacher.
- Your job is to review work done by students and help them learn how to do better."""

        user_message: List[Union[str, Image]] = []
        user_message.append("# A team of students made a mistake on the following task:\n")
        user_message.extend([task_description])

        if len(memory_section) > 0:
            user_message.append(memory_section)

        user_message.append("# Here's the expected answer, which would have been correct:\n")
        user_message.append(expected_answer)

        user_message.append("# Here is the students' answer, which was INCORRECT:\n")
        user_message.append(final_response)

        user_message.append("# Please review the students' work which follows:\n")
        user_message.append("**-----  START OF STUDENTS' WORK  -----**\n\n")
        user_message.append(work_history)
        user_message.append("\n**-----  END OF STUDENTS' WORK  -----**\n\n")

        user_message.append(
            "# Now carefully review the students' work above, explaining in detail what the students did right and what they did wrong.\n"
        )

        self._clear_history()
        await self.call_model(
            summary="Ask the model to learn from this failure",
            system_message_content=sys_message,
            user_content=user_message,
        )
        user_message = [
            "Now put yourself in the mind of the students. What misconception led them to their incorrect answer?"
        ]
        await self.call_model(
            summary="Ask the model to state the misconception",
            system_message_content=sys_message,
            user_content=user_message,
        )

        user_message = [
            "Please express your key insights in the form of short, general advice that will be given to the students. Just one or two sentences, or they won't bother to read it."
        ]
        insight = await self.call_model(
            summary="Ask the model to formulate a concise insight",
            system_message_content=sys_message,
            user_content=user_message,
        )
        return insight

    async def find_index_topics(self, input_string: str) -> List[str]:
        """
        Returns a list of topics related to the given string.
        """
        sys_message = """You are an expert at semantic analysis."""

        user_message: List[Union[str, Image]] = []
        user_message.append("""- My job is to create a thorough index for a book called Task Completion, and I need your help.
- Every paragraph in the book needs to be indexed by all the topics related to various kinds of tasks and strategies for completing them.
- Your job is to read the text below and extract the task-completion topics that are covered.
- The number of topics depends on the length and content of the text. But you should list at least one topic, and potentially many more.
- Each topic you list should be a meaningful phrase composed of a few words. Don't use whole sentences as topics.
- Don't include details that are unrelated to the general nature of the task, or a potential strategy for completing tasks.
- List each topic on a separate line, without any extra text like numbering, or bullets, or any other formatting, because we don't want those things in the index of the book.\n\n""")

        user_message.append("# Text to be indexed\n")
        user_message.append(input_string)

        self._clear_history()
        topics = await self.call_model(
            summary="Ask the model to extract topics", system_message_content=sys_message, user_content=user_message
        )

        # Parse the topics into a list.
        topic_list: List[str] = []
        for line in topics.split("\n"):
            if len(line) > 0:
                topic_list.append(line)

        return topic_list

    async def generalize_task(self, task_description: str, revise: bool | None = True) -> str:
        """
        Attempts to rewrite a task description in a more general form.
        """

        sys_message = """You are a helpful and thoughtful assistant."""

        user_message: List[Union[str, Image]] = [
            "We have been given a task description. Our job is not to complete the task, but merely rephrase the task in simpler, more general terms, if possible. Please reach through the following task description, then explain your understanding of the task in detail, as a single, flat list of all the important points."
        ]
        user_message.append("\n# Task description")
        user_message.append(task_description)

        self._clear_history()
        generalized_task = await self.call_model(
            summary="Ask the model to rephrase the task in a list of important points",
            system_message_content=sys_message,
            user_content=user_message,
        )

        if revise:
            user_message = [
                "Do you see any parts of this list that are irrelevant to actually solving the task? If so, explain which items are irrelevant."
            ]
            await self.call_model(
                summary="Ask the model to identify irrelevant points",
                system_message_content=sys_message,
                user_content=user_message,
            )

            user_message = [
                "Revise your original list to include only the most general terms, those that are critical to solving the task, removing any themes or descriptions that are not essential to the solution. Your final list may be shorter, but do not leave out any part of the task that is needed for solving the task. Do not add any additional commentary either before or after the list."
            ]
            generalized_task = await self.call_model(
                summary="Ask the model to make a final list of general terms",
                system_message_content=sys_message,
                user_content=user_message,
            )

        return generalized_task

    async def validate_insight(self, insight: str, task_description: str) -> bool:
        """
        Judges whether the insight could help solve the task.
        """

        sys_message = """You are a helpful and thoughtful assistant."""

        user_message: List[Union[str, Image]] = [
            """We have been given a potential insight that may or may not be useful for solving a given task.
- First review the following task.
- Then review the insight that follows, and consider whether it might help solve the given task.
- Do not attempt to actually solve the task.
- Reply with a single character, '1' if the insight may be useful, or '0' if it is not."""
        ]
        user_message.append("\n# Task description")
        user_message.append(task_description)
        user_message.append("\n# Possibly useful insight")
        user_message.append(insight)
        self._clear_history()
        response = await self.call_model(
            summary="Ask the model to validate the insight",
            system_message_content=sys_message,
            user_content=user_message,
        )
        return response == "1"

    async def extract_task(self, text: str) -> str | None:
        """
        Returns a task found in the given text, or None if not found.
        """
        sys_message = """You are a helpful and thoughtful assistant."""
        user_message: List[Union[str, Image]] = [
            """Does the following text contain a question or a some task we are being asked to perform?
- If so, please reply with the full question or task description, along with any supporting information, but without adding extra commentary or formatting.
- If the task is just to remember something, that doesn't count as a task, so don't include it.
- If there is no question or task in the text, simply write "None" with no punctuation."""
        ]
        user_message.append("\n# Text to analyze")
        user_message.append(text)
        self._clear_history()
        response = await self.call_model(
            summary="Ask the model to extract a task", system_message_content=sys_message, user_content=user_message
        )
        return response if response != "None" else None

    async def extract_advice(self, text: str) -> str | None:
        """
        Returns advice from the given text, or None if not found.
        """
        sys_message = """You are a helpful and thoughtful assistant."""
        user_message: List[Union[str, Image]] = [
            """Does the following text contain any information or advice that might be useful later?
- If so, please copy the information or advice, adding no extra commentary or formatting.
- If there is no potentially useful information or advice at all, simply write "None" with no punctuation."""
        ]
        user_message.append("\n# Text to analyze")
        user_message.append(text)
        self._clear_history()
        response = await self.call_model(
            summary="Ask the model to extract advice", system_message_content=sys_message, user_content=user_message
        )
        return response if response != "None" else None
