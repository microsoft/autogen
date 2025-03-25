import random
import time
from typing import TYPE_CHECKING, Any, List, Sequence, Tuple, TypedDict

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.base import TaskResult
from autogen_agentchat.messages import AgentEvent, ChatMessage, TextMessage
from autogen_core.models import (
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
)

from .page_logger import PageLogger

if TYPE_CHECKING:
    from ..memory_controller import MemoryControllerConfig


# Following the nested-config pattern, this TypedDict minimizes code changes by encapsulating
# the settings that change frequently, as when loading many settings from a single YAML file.
class ApprenticeConfig(TypedDict, total=False):
    name_of_agent_or_team: str
    disable_prefix_caching: bool
    MemoryController: "MemoryControllerConfig"


class Apprentice:
    """
    A minimal wrapper combining task-centric memory with an agent or team.
    Applications may use the Apprentice class, or they may directly instantiate
    and call the Memory Controller using this class as an example.

    Args:
        client: The client to call the model.
        config: An optional dict that can be used to override the following values:

            - name_of_agent_or_team: The name of the target agent or team for assigning tasks to.
            - disable_prefix_caching: True to disable prefix caching by prepending random ints to the first message.
            - MemoryController: A config dict passed to MemoryController.

        logger: An optional logger. If None, a default logger will be created.
    """

    def __init__(
        self,
        client: ChatCompletionClient,
        config: ApprenticeConfig | None = None,
        logger: PageLogger | None = None,
    ) -> None:
        if logger is None:
            logger = PageLogger({"level": "DEBUG"})
        self.logger = logger

        # Apply default settings and any config overrides.
        self.name_of_agent_or_team = "AssistantAgent"
        self.disable_prefix_caching = False
        memory_controller_config = None
        if config is not None:
            self.name_of_agent_or_team = config.get("name_of_agent_or_team", self.name_of_agent_or_team)
            self.disable_prefix_caching = config.get("disable_prefix_caching", self.disable_prefix_caching)
            memory_controller_config = config.get("MemoryController", memory_controller_config)

        self.client = client
        if self.disable_prefix_caching:
            self.rand = random.Random()
            self.rand.seed(int(time.time() * 1000))

        # Create the MemoryController, which creates the MemoryBank.
        from ..memory_controller import MemoryController

        self.memory_controller = MemoryController(
            reset=True,
            client=self.client,
            task_assignment_callback=self.assign_task_to_agent_or_team,
            config=memory_controller_config,
            logger=self.logger,
        )

    def reset_memory(self) -> None:
        """
        Resets the memory bank.
        """
        self.memory_controller.reset_memory()

    async def handle_user_message(self, text: str, should_await: bool = True) -> str:
        """
        Handles a user message, extracting any advice and assigning a task to the agent.
        """
        self.logger.enter_function()

        # Pass the user message through to the memory controller.
        response = await self.memory_controller.handle_user_message(text, should_await)

        self.logger.leave_function()
        return response

    async def add_task_solution_pair_to_memory(self, task: str, solution: str) -> None:
        """
        Adds a task-solution pair to the memory bank, to be retrieved together later as a combined insight.
        This is useful when the insight is a demonstration of how to solve a given type of task.
        """
        self.logger.enter_function()

        # Pass the task and solution through to the memory controller.
        await self.memory_controller.add_task_solution_pair_to_memory(task, solution)

        self.logger.leave_function()

    async def assign_task(self, task: str, use_memory: bool = True, should_await: bool = True) -> str:
        """
        Assigns a task to the agent, along with any relevant insights/memories.
        """
        self.logger.enter_function()

        # Pass the task through to the memory controller.
        response = await self.memory_controller.assign_task(task, use_memory, should_await)

        self.logger.leave_function()
        return response

    async def train_on_task(self, task: str, expected_answer: str) -> None:
        """
        Repeatedly assigns a task to the completion agent, and tries to learn from failures by creating useful insights as memories.
        """
        self.logger.enter_function()

        # Pass the task through to the memory controller.
        await self.memory_controller.train_on_task(task, expected_answer)

        self.logger.leave_function()

    async def assign_task_to_agent_or_team(self, task: str) -> Tuple[str, str]:
        """
        Passes the given task to the target agent or team.
        """
        self.logger.enter_function()

        # Pass the task through.
        if self.name_of_agent_or_team == "MagenticOneGroupChat":
            response, work_history = await self._assign_task_to_magentic_one(task)
        elif self.name_of_agent_or_team == "AssistantAgent":
            response, work_history = await self._assign_task_to_assistant_agent(task)
        else:
            raise AssertionError("Invalid base agent")

        self.logger.leave_function()
        return response, work_history

    async def _assign_task_to_assistant_agent(self, task: str) -> Tuple[Any, Any]:
        """
        Passes the given task to a newly created AssistantAgent with a generic 6-step system prompt.
        """
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

        if self.disable_prefix_caching:
            # Prepend a random int to disable prefix caching.
            random_str = "({})\n\n".format(self.rand.randint(0, 1000000))
            system_message_content = random_str + system_message_content

        system_message: LLMMessage
        if self.client.model_info["family"] == "o1":
            # No system message allowed, so pass it as the first user message.
            system_message = UserMessage(content=system_message_content, source="User")
        else:
            # System message allowed.
            system_message = SystemMessage(content=system_message_content)

        user_message: LLMMessage = UserMessage(content=task, source="User")
        system_message_list: List[LLMMessage] = [system_message]
        user_message_list: List[LLMMessage] = [user_message]
        input_messages: List[LLMMessage] = system_message_list + user_message_list

        assistant_agent = AssistantAgent(
            "assistant_agent",
            self.client,
            system_message=system_message_content,
        )

        # Get the agent's response to the task.
        task_result: TaskResult = await assistant_agent.run(task=TextMessage(content=task, source="User"))
        messages: Sequence[AgentEvent | ChatMessage] = task_result.messages
        message: AgentEvent | ChatMessage = messages[-1]
        response_str = message.to_text()

        # Log the model call
        self.logger.log_model_task(
            summary="Ask the model to complete the task", input_messages=input_messages, task_result=task_result
        )
        self.logger.info("\n-----  RESPONSE  -----\n\n{}\n".format(response_str))

        # Use the response as the work history as well.
        work_history = response_str

        self.logger.leave_function()
        return response_str, work_history

    async def _assign_task_to_magentic_one(self, task: str) -> Tuple[str, str]:
        """
        Instantiates a MagenticOneGroupChat team, and passes the given task to it.
        """
        self.logger.enter_function()
        self.logger.info(task)

        general_agent = AssistantAgent(
            "general_agent",
            self.client,
            description="A general GPT-4o AI assistant capable of performing a variety of tasks.",
        )

        from autogen_ext.agents.web_surfer import MultimodalWebSurfer

        web_surfer = MultimodalWebSurfer(
            name="web_surfer",
            model_client=self.client,
            downloads_folder="logs",
            debug_dir="logs",
            to_save_screenshots=True,
        )

        from autogen_agentchat.teams import MagenticOneGroupChat

        team = MagenticOneGroupChat(
            [general_agent, web_surfer],
            model_client=self.client,
            max_turns=20,
        )

        # Get the team's response to the task.
        task_result: TaskResult = await team.run(task=task)

        assert isinstance(task_result, TaskResult)
        messages = task_result.messages

        response_str_list: List[str] = []
        for message in messages:
            response_str_list.append(message.to_text())
        response_str = "\n".join(response_str_list)

        self.logger.info("\n-----  RESPONSE  -----\n\n{}\n".format(response_str))

        # MagenticOne's response is the chat history, which we use here as the work history.
        work_history = response_str

        self.logger.leave_function()
        return response_str, work_history
