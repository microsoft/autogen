import time
from typing import List

from autogen_core.components.models import (
    AssistantMessage,
    LLMMessage,
    SystemMessage,
    UserMessage,
    CreateResult,
)

from autogen_core.components import FunctionCall, Image

from ._utils import message_content_to_str, UserContent, text_from_user_content, single_image_from_user_content


class Prompter:
    def __init__(self, client, page_log):
        self.client = client
        self.page_log = page_log
        self.time_spent_in_model_calls = 0.
        self.num_model_calls = 0
        self.start_time = time.time()

        # Create the chat history
        self._chat_history: List[LLMMessage] = []

    async def call_model(self, details, user_content: UserContent = None, system_message=None, keep_these_messages=True):
        # Prepare the input message list
        user_message = UserMessage(content=user_content, source="User")
        if system_message is None:
            system_message = self.default_system_message
        system_message = SystemMessage(content=system_message)

        input_messages = [system_message] + self._chat_history + [user_message]

        # Double check the types of the input messages.
        for message in input_messages:
            for part in message.content:
                if part is None:
                    print("part is None")
                    print("message = ", message)
                assert isinstance(part, str) or isinstance(part, Image), "Invalid message content type: {}".format(type(part))

        # Call the model
        start_time = time.time()

        # create_result, num_input_tokens = self.core.call_model(input_messages)
        num_input_tokens = self.client.count_tokens(input_messages)
        max_input_tokens_per_call = None  # This is a placeholder value.
        if (max_input_tokens_per_call is not None) and (num_input_tokens > max_input_tokens_per_call):
            # The input is too large.
            response = None
        else:
            # Call the model.
            response = await self.client.create(input_messages)


        if response is None:
            parent_page = self.page_log.add_model_call(description="Ask the model",
                details=details + "  ({:,} TOO MANY INPUT TOKENS)".format(num_input_tokens),
                input_messages=input_messages, response=None, num_input_tokens=num_input_tokens, caller='Orchestrator')
            assert False, "TOO MANY INPUT TOKENS"
            response_string = ""
        else:
            assert isinstance(response, CreateResult)
            response_string = response.content
            assert isinstance(response_string, str)
            response_message = AssistantMessage(content=response_string, source="Assistant")
            assert isinstance(response_message, AssistantMessage)

            self.time_spent_in_model_calls += time.time() - start_time
            self.num_model_calls += 1

            # Log the model call
            parent_page = self.page_log.add_model_call(description="Ask the model",
                details=details, input_messages=input_messages, response=response_message,
                num_input_tokens=num_input_tokens, caller='Orchestrator')

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

    async def learn_from_failure(self, task_description, memory_section, final_response, expected_answer,
                                 work_history, final_format_instructions, insights):
        # Try to create an insight to help avoid this failure in the future.

        sys_message = """- You are a patient and thorough teacher.
- Your job is to review work done by students and help them learn how to do better."""

        user_message = []
        user_message.append("# A team of students made a mistake on the following task:\n")
        user_message.extend([task_description])

        if len(memory_section) > 0:
            user_message.append(memory_section)

        if len(final_format_instructions) > 0:
            user_message.append("# The following answer-formatting instructions were given to the students:\n")
            user_message.append(final_format_instructions)

        user_message.append("# Here's the expected answer, which would have been correct:\n")
        user_message.append(expected_answer)

        user_message.append("# Here is the students' answer, which was INCORRECT:\n")
        user_message.append(final_response)

        user_message.append("# Please review the students' work which follows:\n")
        user_message.append("**-----  START OF STUDENTS' WORK  -----**\n\n")
        user_message.append(work_history)
        user_message.append("\n**-----  END OF STUDENTS' WORK  -----**\n\n")

        user_message.append(
            "# Now carefully review the students' work above, explaining in detail what the students did right and what they did wrong.\n")

        self.clear_history()
        response1, page = await self.call_model(
            system_message=sys_message,
            user_content=user_message,
            details="to learn from this failure")

        user_message = [
            "Now put yourself in the mind of the students. What misconception led them to their incorrect answer?"]
        response2, page = await self.call_model(
            system_message=sys_message,
            user_content=user_message,
            details="to state the misconception")

        user_message = ["Please express your key insights in the form of short, general advice that will be given to the students. Just one or two sentences, or they won't bother to read it."]
        # if len(insights) > 0:
        #     memory_section = "\n## The following insights and advice were given to the students previously, but they didn't help. So do not repeat any of the following:\n"
        #     for insight in insights:
        #         memory_section += ('- ' + insight + '\n')
        #     user_message.append(memory_section)

        insight, page = await self.call_model(
            system_message=sys_message,
            user_content=user_message,
            details="to formulate a concise insight")

        return insight

    async def find_index_topics(self, input_string):
        # Returns a list of topics related to the input string.

        sys_message = """You are an expert at semantic analysis."""

        user_message = []
        user_message.append("""- My job is to create a thorough index for a book called Task Completion, and I need your help.
- Every paragraph in the book needs to be indexed by all the topics related to various kinds of tasks and strategies for completing them.
- Your job is to read the text below and extract the task-completion topics that are covered.
- The number of topics depends on the length and content of the text. But you should list at least one topic, and potentially many more.
- Each topic you list should be a meaningful phrase composed of a few words. Don't use whole sentences as topics.
- Don't include details that are unrelated to the general nature of the task, or a potential strategy for completing tasks.
- List each topic on a separate line, without any extra text like numbering, or bullets, or any other formatting, because we don't want those things in the index of the book.\n\n""")

        user_message.append("# Text to be indexed\n")
        user_message.append(input_string)

        self.clear_history()
        topics, page = await self.call_model(
            system_message=sys_message,
            user_content=user_message,
            details="to extract topics")

        # Parse the topics into a python list.
        topic_list = []
        for line in topics.split("\n"):
            if (line is not None) and (len(line) > 0):
                topic_list.append(line)

        return topic_list

    async def generalize_task(self, task_description):
        # Returns a list of topics related to the input string.

        sys_message = """You are a helpful and thoughtful assistant."""

        user_message = ["We have been given a task description. Our job is not to complete the task, but merely rephrase the task in simpler, more general terms, if possible. Please reach through the following task description, then explain your understanding of the task in detail, as a single, flat list of all the important points."]
        user_message.append("\n# Task description")
        user_message.append(task_description)

        self.clear_history()
        response1, page = await self.call_model(
            system_message=sys_message,
            user_content=user_message,
            details="to rephrase the task in a list of important points")

        user_message = ["Do you see any parts of this list that are irrelevant to actually solving the task? If so, explain which items are irrelevant."]
        response2, page = await self.call_model(
            system_message=sys_message,
            user_content=user_message,
            details="to identify irrelevant points")

        user_message = ["Revise your original list to include only the most general terms, those that are critical to solving the task, removing any themes or descriptions that are not essential to the solution. Your final list may be shorter, but do not leave out any part of the task that is needed for solving the task. Do not add any additional commentary either before or after the list."]
        generalized_task, page = await self.call_model(
            system_message=sys_message,
            user_content=user_message,
            details="to make a final list of general terms")

        return generalized_task

    async def validate_insights(self, insights, task_description):
        # Returns only the insights that the client verifies are relevant to the task.

        sys_message = """You are a helpful and thoughtful assistant."""

        user_message = ["""We have been given a list of insights that may or may not be useful for solving the given task. 
- First review the following task.
- Then review the list of insights that follow, and discuss which ones could be useful in solving the given task.
- Do not attempt to actually solve the task. That will come later."""]
        user_message.append("\n# Task description")
        user_message.append(task_description)
        user_message.append("\n# Possibly useful insights")
        user_message.extend(insights)
        self.clear_history()
        response1, page = await self.call_model(
            system_message=sys_message,
            user_content=user_message,
            details="to review the task and insights")

        user_message = ["""Now output a verbatim copy the insights that you decided are relevant to the task.
- The original list of insights is provided below for reference.
- If an insight is not relevant to the task, simply omit it from your response.
- Do not add any additional commentary either before or after the relevant tasks.
- If none of the tasks are relevant, simply write "None"."""]
        user_message.append("\n# Original list of possibly useful insights")
        user_message.extend(insights)
        validated_insights, page = await self.call_model(
            system_message=sys_message,
            user_content=user_message,
            details="to list the relevant insights")

        return [validated_insights] if validated_insights != "None" else []
