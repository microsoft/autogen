from typing import List

from autogen_core.models import (
    AssistantMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
    CreateResult,
)

from ._utils import UserContent


class Grader:
    def __init__(self, client, page_log):
        self.client = client
        self.page_log = page_log

        # Create the chat history
        self._chat_history: List[LLMMessage] = []

    async def call_model(self, details, user_content: UserContent = None, system_message=None, keep_these_messages=True):
        # Prepare the input message list
        user_message = UserMessage(content=user_content, source="User")
        if system_message is None:
            system_message = "You are a helpful assistant."
        system_message = SystemMessage(content=system_message)

        input_messages = [system_message] + self._chat_history + [user_message]

        # Call the model.
        response = await self.client.create(input_messages)
        assert isinstance(response, CreateResult)
        response_string = response.content
        assert isinstance(response_string, str)
        response_message = AssistantMessage(content=response_string, source="Assistant")
        assert isinstance(response_message, AssistantMessage)

        # Log the model call
        parent_page = self.page_log.add_model_call(description="Ask the model",
            details=details, input_messages=input_messages, response=response, caller='Grader')

        # Manage the chat history
        if keep_these_messages:
            self._chat_history.append(user_message)
            self._chat_history.append(response_message)

        # Return the response as a string for now
        return response_string, parent_page

    def remove_last_turn(self):
        if len(self._chat_history) > 0:
            self._chat_history.pop()

    def clear_history(self):
        self._chat_history = []

    async def is_response_correct(self, task_description, response_to_be_graded, correct_answer):
        # Returns only the insights that the client verifies are relevant to the task.
        page = self.page_log.begin_page(
            summary="Grader.is_response_correct",
            details="",
            method_call="Grader.is_response_correct")

        sys_message = """You are a helpful and thoughtful assistant."""

        user_message = ["""Your job is to extract a possible answer to the following question from the given text.
- First review the following task.
- Then review the text that follows, which may an answer, plus reasoning that led to the answer.
- Do not attempt to actually solve the task yourself.
- Don't try to judge whether the reasoning steps were correct.
- Simply respond by summarizing the answer described in the text, omitting any other parts of the text.
- If no answer is present can be extracted from the text, simply reply "None"."""]
        user_message.append("\n# Task description")
        user_message.append(task_description)
        user_message.append("\n# Text that may contain an answer")
        user_message.append(response_to_be_graded)
        self.clear_history()
        extracted_answer, _ = await self.call_model(
            system_message=sys_message,
            user_content=user_message,
            details="to extract the answer")
        page.add_lines("Extracted answer: " + extracted_answer)

        user_message = ["""Your job is to decide whether a given answer to a task is correct or not.
- You will be given the task description and the correct, gold-standard answer, along with the answer to be graded.
- In general, an answer is correct if it is equivalent to the correct answer.
- Specifically, the given answer must contain the important information from the correct answer, and must not in any way contradict the correct answer.
- Ignore any differences of grammar, spelling mistakes, punctuation, capitalization, formatting, or extra commentary.
- An answer should be considered correct if it omits information that is clearly inferred.
  - For instance, if the correct answer is "Paris, France", the answer "Paris" should be considered correct.
- Respond with a single character: '1' if the answer to be graded is correct", '0' if not."""]
        user_message.append("\n# Task description")
        user_message.append(task_description)
        user_message.append("\n# Correct answer")
        user_message.append(correct_answer)
        user_message.append("\n# Answer to be graded")
        user_message.append(extracted_answer)
        self.clear_history()
        decision, _ = await self.call_model(
            system_message=sys_message,
            user_content=user_message,
            details="to check the answer for correctness")
        page.add_lines("Decision: " + decision)

        self.page_log.finish_page(page)
        return decision == "1", extracted_answer
