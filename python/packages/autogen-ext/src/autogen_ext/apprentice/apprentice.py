from .agent_wrapper import AgentWrapper
from .agentic_memory_controller import AgenticMemoryController


class Apprentice:
    def __init__(self, settings, evaluator, client, logger):
        self.settings = settings
        self.evaluator = evaluator
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

    def reset_memory(self):
        if self.memory_controller is not None:
            self.memory_controller.reset_memory()

    async def handle_user_message(self, text, should_await=True):
        """A foreground operation, intended for immediate response to the user."""
        self.logger.enter_function()

        # Pass the user message through to the memory controller.
        response = await self.memory_controller.handle_user_message(text, should_await)

        self.logger.leave_function()
        return response

    async def learn_from_demonstration(self, task, demonstration):
        """A foreground operation, assuming that the task and demonstration are already known."""
        self.logger.enter_function()

        # Pass the task and demonstration through to the memory controller.
        await self.memory_controller.learn_from_demonstration(task, demonstration)

        self.logger.leave_function()

    async def assign_task(self, task: str, use_memory: bool = True, should_await: bool = True):
        """
        Assigns a task to the agent, along with any relevant insights/memories.
        """
        self.logger.enter_function()

        # Pass the task through to the memory controller.
        response = await self.memory_controller.assign_task(task, use_memory, should_await)

        self.logger.leave_function()
        return response

    async def train_on_task(self, task, expected_answer):
        """A background operation, not intended for immediate response."""
        self.logger.enter_function()

        # Pass the task through to the memory controller.
        await self.memory_controller.train_on_task(task, expected_answer)

        self.logger.leave_function()
