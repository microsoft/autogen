from .agent_wrapper import AgentWrapper
from .agentic_memory_controller import AgenticMemoryController


class Apprentice:
    """
    Wraps the combination of agentic memory and a base agent.

    Args:
        settings: The settings for the apprentice.
        client: The client to call the model.
        logger: The logger to log the model calls.

    Methods:
        reset_memory: Resets the memory bank.
        assign_task: Assigns a task to the agent, along with any relevant insights/memories.
        handle_user_message: Handles a user message, extracting any advice and assigning a task to the agent.
        add_task_solution_pair_to_memory: Adds a task-solution pair to the memory bank, to be retrieved together later as a combined insight.
        train_on_task: Repeatedly assigns a task to the completion agent, and tries to learn from failures by creating useful insights as memories.
    """
    def __init__(self, settings, client, logger) -> None:
        self.settings = settings
        self.client = client
        self.logger = logger

        # Create the agent wrapper, which creates the base agent.
        self.agent_settings = settings["AgentWrapper"]
        self.agent = AgentWrapper(settings=self.agent_settings, client=self.client, logger=self.logger)

        # Create the AgenticMemoryController, which creates the AgenticMemoryBank.
        self.memory_controller = AgenticMemoryController(
            settings=self.settings["AgenticMemoryController"],
            agent=self.agent,
            reset=True,
            client=self.client,
            logger=self.logger,
        )

    def reset_memory(self) -> None:
        """
        Resets the memory bank.
        """
        if self.memory_controller is not None:
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

    async def add_task_solution_pair_to_memory(self, task, solution) -> None:
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
