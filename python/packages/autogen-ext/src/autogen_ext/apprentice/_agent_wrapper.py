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
    def __init__(self, settings, client, logger):
        self.settings = settings
        self.client = client
        self.logger = logger
        self.base_agent_name = self.settings["base_agent"]

    async def assign_task(self, task):
        """
        Assigns a task to the base agent.
        """
        self.logger.enter_function()

        # Pass the task through to the base agent.
        if self.base_agent_name == "MagenticOneGroupChat":
            response, work_history = await self.assign_task_to_magentic_one(task)
        elif self.base_agent_name == "thin_agent":
            response, work_history = await self.assign_task_to_thin_agent(task)
        else:
            assert False, "Invalid base agent"

        self.logger.leave_function()
        return response, work_history

    async def assign_task_to_thin_agent(self, task):
        self.logger.enter_function()

        self.logger.info(task)

        system_message_content = """You are a helpful and thoughtful assistant.
In responding to every user message, you follow the same multi-step process given here:
1. Explain your understanding of the user message in detail, covering all the important points.
2. List as many possible responses as you can think of.
3. Carefully list and weigh the pros and cons (if any) of each possible response.
4. Critique the pros and cons above, looking for any flaws in your reasoning. But don't make up flaws that don't exist.
5. Decide on the best response, looping back to step 1 if none of the responses are satisfactory.
6. Finish by providing your final response in the particular format requested by the user."""
        if self.client.model_info["family"] == "o1":
            # No system message allowed, so pass it as the first user message.
            system_message = UserMessage(content=system_message_content, source="User")
        else:
            # System message allowed.
            system_message = SystemMessage(content=system_message_content)

        user_message = UserMessage(content=task, source="User")
        input_messages = [system_message] + [user_message]

        response = await self.client.create(input_messages)
        response_str = response.content

        # Log the model call
        self.logger.add_model_call(summary="Ask the model to complete the task",
                                     input_messages=input_messages, response=response)
        self.logger.info("\n-----  RESPONSE  -----\n\n{}\n".format(response_str))

        # Use the response as the work history as well.
        work_history = response_str

        self.logger.leave_function()
        return response_str, work_history

    async def assign_task_to_magentic_one(self, task) -> Tuple[str, str]:
        self.logger.enter_function()

        self.logger.info(task)

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
        self.logger.info("\n-----  RESPONSE  -----\n\n{}\n".format(response_str))

        # MagenticOne's response is the chat history, which we use here as the work history.
        work_history = response_str

        self.logger.leave_function()
        return response_str, work_history
