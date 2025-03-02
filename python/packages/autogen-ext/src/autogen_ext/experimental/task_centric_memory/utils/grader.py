from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple, Union

from autogen_core import Image
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    SystemMessage,
    UserMessage,
)

from ._functions import UserContent
from .page_logger import PageLogger

if TYPE_CHECKING:
    from .apprentice import Apprentice


class Grader:
    """
    Runs basic tests, and determines task success without limitation to string matches.

    Args:
        client: The client to call the model.
        logger: An optional logger. If None, no logging will be performed.
    """

    def __init__(self, client: ChatCompletionClient, logger: PageLogger | None = None) -> None:
        if logger is None:
            logger = PageLogger()  # Nothing will be logged by this object.
        self.logger = logger
        self.client = client

        # Create the chat history
        self._chat_history: List[LLMMessage] = []

    async def test_apprentice(
        self,
        apprentice: Apprentice,
        task_description: str,
        expected_answer: str,
        num_trials: int,
        use_memory: bool,
        client: ChatCompletionClient,
    ) -> Tuple[int, int]:
        self.logger.enter_function()

        self.logger.info("Testing the apprentice on the given task.\n")

        num_successes = 0

        for trial in range(num_trials):
            self.logger.info("\n-----  TRIAL {}  -----\n".format(trial + 1))
            self.logger.info("Try to solve the task.\n")
            response = await apprentice.assign_task(task_description, use_memory=use_memory)
            response_is_correct, extracted_answer = await self.is_response_correct(
                task_description, response, expected_answer
            )
            self.logger.info("Extracted answer:  {}".format(extracted_answer))
            if response_is_correct:
                self.logger.info("Answer is CORRECT.\n")
                num_successes += 1
            else:
                self.logger.info("Answer is INCORRECT.\n")

        self.logger.info("\nSuccess rate:  {}%\n".format(round((num_successes / num_trials) * 100)))
        self.logger.leave_function()
        return num_successes, num_trials

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
            system_message_content = "You are a helpful assistant."
        system_message: LLMMessage
        if self.client.model_info["family"] == "o1":
            # No system message allowed, so pass it as the first user message.
            system_message = UserMessage(content=system_message_content, source="User")
        else:
            # System message allowed.
            system_message = SystemMessage(content=system_message_content)
        user_message = UserMessage(content=user_content, source="User")
        input_messages = [system_message] + self._chat_history + [user_message]

        # Call the model.
        response = await self.client.create(input_messages)
        assert isinstance(response, CreateResult)
        response_string = response.content
        assert isinstance(response_string, str)
        response_message = AssistantMessage(content=response_string, source="Assistant")
        assert isinstance(response_message, AssistantMessage)

        # Log the model call
        self.logger.log_model_call(summary=summary, input_messages=input_messages, response=response)

        # Manage the chat history
        if keep_these_messages:
            self._chat_history.append(user_message)
            self._chat_history.append(response_message)

        # Return the response as a string
        return response_string

    def _clear_history(self) -> None:
        """
        Empties the message list containing the chat history.
        """
        self._chat_history = []

    async def is_response_correct(
        self, task_description: str, response_to_be_graded: str, correct_answer: str
    ) -> Tuple[bool, str]:
        """
        Determines whether the response is equivalent to the task's correct answer.
        """
        self.logger.enter_function()

        sys_message = """You are a helpful and thoughtful assistant."""

        # Ask the model to extract the answer from the response.
        user_message: List[Union[str, Image]] = []
        user_message.append("""Your job is to extract a possible answer to the following question from the given text.
- First review the following task.
- Then review the text that follows, which may an answer, plus reasoning that led to the answer.
- Do not attempt to actually solve the task yourself.
- Don't try to judge whether the reasoning steps were correct.
- Simply respond by summarizing the answer described in the text, omitting any other parts of the text.
- If no answer is present can be extracted from the text, simply reply "None".""")
        user_message.append("\n# Task description")
        user_message.append(task_description)
        user_message.append("\n# Text that may contain an answer")
        user_message.append(response_to_be_graded)
        user_message_arg: UserContent = user_message
        self._clear_history()
        extracted_answer = await self.call_model(
            summary="Ask the model to extract the answer",
            system_message_content=sys_message,
            user_content=user_message_arg,
        )
        self.logger.info("Extracted answer: " + extracted_answer)

        # Ask the model to check the answer for correctness.
        user_message = [
            """Your job is to decide whether a given answer to a task is correct or not.
- You will be given the task description and the correct, gold-standard answer, along with the answer to be graded.
- In general, an answer is correct if it is equivalent to the correct answer.
- Specifically, the given answer must contain the important information from the correct answer, and must not in any way contradict the correct answer.
- Ignore any differences of grammar, spelling mistakes, punctuation, capitalization, formatting, or extra commentary.
- An answer should be considered correct if it omits information that is clearly inferred.
  - For instance, if the correct answer is "Paris, France", the answer "Paris" should be considered correct.
- Respond with a single character: '1' if the answer to be graded is correct", '0' if not."""
        ]
        user_message.append("\n# Task description")
        user_message.append(task_description)
        user_message.append("\n# Correct answer")
        user_message.append(correct_answer)
        user_message.append("\n# Answer to be graded")
        user_message.append(extracted_answer)
        self._clear_history()
        decision = await self.call_model(
            summary="Ask the model to check the answer for correctness",
            system_message_content=sys_message,
            user_content=user_message,
        )
        self.logger.info("Decision: " + decision)

        self.logger.leave_function()
        return decision == "1", extracted_answer
