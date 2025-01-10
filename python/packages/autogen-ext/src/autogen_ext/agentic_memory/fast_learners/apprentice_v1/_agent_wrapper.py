from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.agents.web_surfer._utils import message_content_to_str
from autogen_agentchat.ui._console import Console
from autogen_core.models import (
    SystemMessage,
    UserMessage,
)
from typing import Tuple


class AgentWrapper:
    def __init__(self, settings, client, page_log):
        self.settings = settings
        self.client = client
        self.page_log = page_log
        self.base_agent_name = self.settings["base_agent"]

    async def assign_task(self, task):
        """
        Assigns a task to the base agent.
        """
        page = self.page_log.begin_page(
            summary="AgentWrapper.assign_task",
            details="",
            method_call="AgentWrapper.assign_task")

        # Pass the task through to the base agent.
        if self.base_agent_name == "MagenticOneGroupChat":
            response, work_history = await self.assign_task_to_magentic_one(task)
        elif self.base_agent_name == "thin_agent":
            response, work_history = await self.assign_task_to_thin_agent(task)
        else:
            assert False, "Invalid base agent"

        self.page_log.finish_page(page)
        return response, work_history

    async def assign_task_to_thin_agent(self, task):
        page = self.page_log.begin_page(
            summary="AgentWrapper.assign_task_to_thin_agent",
            details='',
            method_call="AgentWrapper.assign_task_to_thin_agent")

        page.add_lines(task)

        system_message_content = """You are a helpful and thoughtful assistant.
In responding to every user message, you follow the same multi-step process given here:
1. Explain your understanding of the user message in detail, covering all the important points.
2. List as many possible responses as you can think of.
3. Carefully list and weigh the pros and cons (if any) of each possible response.
4. Critique the pros and cons above, looking for any flaws in your reasoning. But don't make up flaws that don't exist.
5. Decide on the best response, looping back to step 1 if none of the responses are satisfactory.
6. Finish by providing your final response in the particular format requested by the user."""

        system_message = SystemMessage(content=system_message_content)
        user_message = UserMessage(content=task, source="User")

        input_messages = [system_message] + [user_message]
        response = await self.client.create(input_messages)
        response_str = response.content

        # Log the model call
        self.page_log.add_model_call(description="Ask the model",
                                     details="to complete the task", input_messages=input_messages,
                                     response=response,
                                     num_input_tokens=0, caller='assign_task_to_client')
        page.add_lines("\n-----  RESPONSE  -----\n\n{}\n".format(response_str), flush=True)

        # Use the response as the work history as well.
        work_history = response_str

        self.page_log.finish_page(page)
        return response_str, work_history

    async def assign_task_to_magentic_one(self, task) -> Tuple[str, str]:
        page = self.page_log.begin_page(
            summary="AgentWrapper.assign_task_to_magentic_one",
            details='',
            method_call="AgentWrapper.assign_task_to_magentic_one")

        page.add_lines(task)

        general_agent = AssistantAgent(
            "general_agent",
            self.client,
            description="A general GPT-4o AI assistant capable of performing a variety of tasks.", )

        web_surfer = MultimodalWebSurfer(
            name="web_surfer",
            model_client=self.client,
            downloads_folder="logs",
            debug_dir="logs",
            to_save_screenshots=True,
        )

        team = MagenticOneGroupChat(
            [general_agent, web_surfer],
            model_client=self.client,
            max_turns=20,
        )

        # Get the team's text response to the task.
        stream = team.run_stream(task=task)
        task_result = await Console(stream)
        response_str = "\n".join([message_content_to_str(message.content) for message in task_result.messages])
        page.add_lines("\n-----  RESPONSE  -----\n\n{}\n".format(response_str), flush=True)

        # MagenticOne's response is the chat history, which we use here as the work history.
        work_history = response_str

        self.page_log.finish_page(page)
        return response_str, work_history
