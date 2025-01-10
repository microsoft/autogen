from ._agentic_memory_controller import AgenticMemoryController
from ._agent_wrapper import AgentWrapper


class FastLearner:
    def __init__(self, settings, evaluator, client, page_log):
        self.settings = settings
        self.evaluator = evaluator
        self.client = client
        self.page_log = page_log

        # Create the agent wrapper, which creates the base agent.
        self.agent_settings = settings["AgentWrapper"]
        self.agent = AgentWrapper(settings=self.agent_settings, client=self.client, page_log=self.page_log)

        # Create the AgenticMemoryController, which creates the AgenticMemoryBank.
        self.memory_controller = AgenticMemoryController(
            settings=self.settings["AgenticMemoryController"],
            agent=self.agent,
            reset=False,
            client=self.client,
            page_log=self.page_log
        )

    def reset_memory(self):
        if self.memory_controller is not None:
            self.memory_controller.reset_memory()

    async def handle_user_message(self, text, should_await=True):
        """A foreground operation, intended for immediate response to the user."""
        page = self.page_log.begin_page(
            summary="FastLearner.handle_user_message",
            details="",
            method_call="FastLearner.handle_user_message")

        # Pass the user message through to the memory controller.
        response = await self.memory_controller.handle_user_message(text, should_await)

        self.page_log.finish_page(page)
        return response

    async def learn_from_demonstration(self, task, demonstration):
        """A foreground operation, assuming that the task and demonstration are already known."""
        page = self.page_log.begin_page(
            summary="FastLearner.learn_from_demonstration",
            details="",
            method_call="FastLearner.learn_from_demonstration")

        # Pass the task and demonstration through to the memory controller.
        await self.memory_controller.learn_from_demonstration(task, demonstration)

        self.page_log.finish_page(page)

    async def assign_task(self, task: str, use_memory: bool = True, should_await: bool = True):
        """
        Assigns a task to the agent, along with any relevant insights/memories.
        """
        page = self.page_log.begin_page(
            summary="FastLearner.assign_task",
            details="",
            method_call="FastLearner.assign_task")

        # Pass the task through to the memory controller.
        response = await self.memory_controller.assign_task(task, use_memory, should_await)

        self.page_log.finish_page(page)
        return response

    async def train_on_task(self, task, expected_answer, final_format_instructions, max_train_trials, max_test_trials):
        """A background operation, not intended for immediate response."""
        page = self.page_log.begin_page(
            summary="FastLearner.train_on_task",
            details="",
            method_call="FastLearner.train_on_task")

        # Pass the task through to the memory controller.
        await self.memory_controller.train_on_task(task, expected_answer, final_format_instructions,
            max_train_trials, max_test_trials)

        self.page_log.finish_page(page)
