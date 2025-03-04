from typing import TYPE_CHECKING, Awaitable, Callable, List, Tuple, TypedDict

from autogen_core.models import (
    ChatCompletionClient,
)

from ._memory_bank import Memo, MemoryBank
from ._prompter import Prompter

if TYPE_CHECKING:
    from ._memory_bank import MemoryBankConfig
from .utils.grader import Grader
from .utils.page_logger import PageLogger


# Following the nested-config pattern, this TypedDict minimizes code changes by encapsulating
# the settings that change frequently, as when loading many settings from a single YAML file.
class MemoryControllerConfig(TypedDict, total=False):
    max_train_trials: int
    max_test_trials: int
    MemoryBank: "MemoryBankConfig"


class MemoryController:
    """
    (EXPERIMENTAL, RESEARCH IN PROGRESS)

    Implements fast, memory-based learning, and manages the flow of information to and from a memory bank.

    Args:
        reset: True to empty the memory bank before starting.
        client: The model client to use internally.
        task_assignment_callback: An optional callback used to assign a task to any agent managed by the caller.
        config: An optional dict that can be used to override the following values:

            - max_train_trials: The maximum number of learning iterations to attempt when training on a task.
            - max_test_trials: The total number of attempts made when testing for failure on a task.
            - MemoryBank: A config dict passed to MemoryBank.

        logger: An optional logger. If None, a default logger will be created.

    Example:

        The `task-centric-memory` extra first needs to be installed:

        .. code-block:: bash

            pip install "autogen-ext[task-centric-memory]"

        The following code snippet shows how to use this class for the most basic storage and retrieval of memories.:

        .. code-block:: python

            import asyncio
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_ext.experimental.task_centric_memory import MemoryController
            from autogen_ext.experimental.task_centric_memory.utils import PageLogger


            async def main() -> None:
                client = OpenAIChatCompletionClient(model="gpt-4o")
                logger = PageLogger(config={"level": "DEBUG", "path": "./pagelogs/quickstart"})  # Optional, but very useful.
                memory_controller = MemoryController(reset=True, client=client, logger=logger)

                # Add a few task-insight pairs as memories, where an insight can be any string that may help solve the task.
                await memory_controller.add_memo(task="What color do I like?", insight="Deep blue is my favorite color")
                await memory_controller.add_memo(task="What's another color I like?", insight="I really like cyan")
                await memory_controller.add_memo(task="What's my favorite food?", insight="Halibut is my favorite")

                # Retrieve memories for a new task that's related to only two of the stored memories.
                memos = await memory_controller.retrieve_relevant_memos(task="What colors do I like most?")
                print("{} memories retrieved".format(len(memos)))
                for memo in memos:
                    print("- " + memo.insight)


            asyncio.run(main())
    """

    def __init__(
        self,
        reset: bool,
        client: ChatCompletionClient,
        task_assignment_callback: Callable[[str], Awaitable[Tuple[str, str]]] | None = None,
        config: MemoryControllerConfig | None = None,
        logger: PageLogger | None = None,
    ) -> None:
        if logger is None:
            logger = PageLogger({"level": "DEBUG"})
        self.logger = logger
        self.logger.enter_function()

        # Apply default settings and any config overrides.
        self.max_train_trials = 10
        self.max_test_trials = 3
        memory_bank_config = None
        if config is not None:
            self.max_train_trials = config.get("max_train_trials", self.max_train_trials)
            self.max_test_trials = config.get("max_test_trials", self.max_test_trials)
            memory_bank_config = config.get("MemoryBank", memory_bank_config)

        self.client = client
        self.task_assignment_callback = task_assignment_callback
        self.prompter = Prompter(client, logger)
        self.memory_bank = MemoryBank(reset=reset, config=memory_bank_config, logger=logger)
        self.grader = Grader(client, logger)
        self.logger.leave_function()

    def reset_memory(self) -> None:
        """
        Empties the memory bank in RAM and on disk.
        """
        self.memory_bank.reset()

    async def train_on_task(self, task: str, expected_answer: str) -> None:
        """
        Repeatedly assigns a task to the agent, and tries to learn from failures by creating useful insights as memories.
        """
        self.logger.enter_function()
        self.logger.info("Iterate on the task, possibly discovering a useful new insight.\n")
        _, insight = await self._iterate_on_task(task, expected_answer)
        if insight is None:
            self.logger.info("No useful insight was discovered.\n")
        else:
            self.logger.info("A new insight was created:\n{}".format(insight))
            await self.add_memo(insight, task)
        self.logger.leave_function()

    async def test_on_task(self, task: str, expected_answer: str, num_trials: int = 1) -> Tuple[str, int, int]:
        """
        Assigns a task to the agent, along with any relevant memos retrieved from memory.
        """
        self.logger.enter_function()
        assert self.task_assignment_callback is not None
        response = ""
        num_successes = 0

        for trial in range(num_trials):
            self.logger.info("\n-----  TRIAL {}  -----\n".format(trial + 1))
            task_plus_insights = task

            # Try to retrieve any relevant memories from the DB.
            filtered_memos = await self.retrieve_relevant_memos(task)
            filtered_insights = [memo.insight for memo in filtered_memos]
            if len(filtered_insights) > 0:
                self.logger.info("Relevant insights were retrieved from memory.\n")
                memory_section = self._format_memory_section(filtered_insights)
                if len(memory_section) > 0:
                    task_plus_insights = task + "\n\n" + memory_section

            # Attempt to solve the task.
            self.logger.info("Try to solve the task.\n")
            response, _ = await self.task_assignment_callback(task_plus_insights)

            # Check if the response is correct.
            response_is_correct, extracted_answer = await self.grader.is_response_correct(
                task, response, expected_answer
            )
            self.logger.info("Extracted answer:  {}".format(extracted_answer))
            if response_is_correct:
                self.logger.info("Answer is CORRECT.\n")
                num_successes += 1
            else:
                self.logger.info("Answer is INCORRECT.\n")

        # Calculate the success rate as a percentage, rounded to the nearest whole number.
        self.logger.info("\nSuccess rate:  {}%\n".format(round((num_successes / num_trials) * 100)))
        self.logger.leave_function()
        return response, num_successes, num_trials

    async def add_memo(self, insight: str, task: None | str = None, index_on_both: bool = True) -> None:
        """
        Adds one insight to the memory bank, using the task (if provided) as context.
        """
        self.logger.enter_function()

        generalized_task = ""
        if task is not None:
            self.logger.info("\nGIVEN TASK:")
            self.logger.info(task)
            # Generalize the task.
            generalized_task = await self.prompter.generalize_task(task)

        self.logger.info("\nGIVEN INSIGHT:")
        self.logger.info(insight)

        # Get a list of topics from the insight and the task (if provided).
        if task is None:
            text_to_index = insight
            self.logger.info("\nTOPICS EXTRACTED FROM INSIGHT:")
        else:
            if index_on_both:
                text_to_index = generalized_task.strip() + "\n(Hint:  " + insight + ")"
                self.logger.info("\nTOPICS EXTRACTED FROM TASK AND INSIGHT COMBINED:")
            else:
                text_to_index = task
                self.logger.info("\nTOPICS EXTRACTED FROM TASK:")

        topics = await self.prompter.find_index_topics(text_to_index)
        self.logger.info("\n".join(topics))
        self.logger.info("")

        # Add the insight to the memory bank.
        self.memory_bank.add_memo(insight, topics, task)
        self.logger.leave_function()

    async def add_task_solution_pair_to_memory(self, task: str, solution: str) -> None:
        """
        Adds a task-solution pair to the memory bank, to be retrieved together later as a combined insight.
        This is useful when the task-solution pair is an exemplar of solving a task related to some other task.
        """
        self.logger.enter_function()

        self.logger.info("\nEXAMPLE TASK:")
        self.logger.info(task)

        self.logger.info("\nEXAMPLE SOLUTION:")
        self.logger.info(solution)

        # Get a list of topics from the task.
        topics = await self.prompter.find_index_topics(task.strip())
        self.logger.info("\nTOPICS EXTRACTED FROM TASK:")
        self.logger.info("\n".join(topics))
        self.logger.info("")

        # Add the task and solution (as a combined insight) to the memory bank.
        self.memory_bank.add_task_with_solution(task=task, solution=solution, topics=topics)
        self.logger.leave_function()

    async def retrieve_relevant_memos(self, task: str) -> List[Memo]:
        """
        Retrieves any memos from memory that seem relevant to the task.
        """
        self.logger.enter_function()

        if self.memory_bank.contains_memos():
            self.logger.info("\nCURRENT TASK:")
            self.logger.info(task)

            # Get a list of topics from the generalized task.
            generalized_task = await self.prompter.generalize_task(task)
            task_topics = await self.prompter.find_index_topics(generalized_task)
            self.logger.info("\nTOPICS EXTRACTED FROM TASK:")
            self.logger.info("\n".join(task_topics))
            self.logger.info("")

            # Retrieve relevant memos from the memory bank.
            memo_list = self.memory_bank.get_relevant_memos(topics=task_topics)

            # Apply a final validation stage to keep only the memos that the LLM concludes are sufficiently relevant.
            validated_memos: List[Memo] = []
            for memo in memo_list:
                if await self.prompter.validate_insight(memo.insight, task):
                    validated_memos.append(memo)

            self.logger.info("\n{} VALIDATED MEMOS".format(len(validated_memos)))
            for memo in validated_memos:
                if memo.task is not None:
                    self.logger.info("\n  TASK: {}".format(memo.task))
                self.logger.info("\n  INSIGHT: {}".format(memo.insight))
        else:
            self.logger.info("\nNO SUFFICIENTLY RELEVANT MEMOS WERE FOUND IN MEMORY")
            validated_memos = []

        self.logger.leave_function()
        return validated_memos

    def _format_memory_section(self, memories: List[str]) -> str:
        """
        Formats a list of memories as a section for appending to a task description.
        """
        memory_section = ""
        if len(memories) > 0:
            memory_section = "## Important insights that may help solve tasks like this\n"
            for mem in memories:
                memory_section += "- " + mem + "\n"
        return memory_section

    async def _test_for_failure(
        self, task: str, task_plus_insights: str, expected_answer: str
    ) -> Tuple[bool, str, str]:
        """
        Attempts to solve the given task multiple times to find a failure case to learn from.
        """
        self.logger.enter_function()
        self.logger.info("\nTask description, including any insights:  {}".format(task_plus_insights))
        self.logger.info("\nExpected answer:  {}\n".format(expected_answer))

        assert self.task_assignment_callback is not None
        failure_found = False
        response, work_history = "", ""

        for trial in range(self.max_test_trials):
            self.logger.info("\n-----  TRIAL {}  -----\n".format(trial + 1))

            # Attempt to solve the task.
            self.logger.info("Try to solve the task.")
            response, work_history = await self.task_assignment_callback(task_plus_insights)

            response_is_correct, extracted_answer = await self.grader.is_response_correct(
                task, response, expected_answer
            )
            self.logger.info("Extracted answer:  {}".format(extracted_answer))
            if response_is_correct:
                self.logger.info("Answer is CORRECT.\n")
            else:
                self.logger.info("Answer is INCORRECT.\n  Stop testing, and return the details of the failure.\n")
                failure_found = True
                break

        self.logger.leave_function()
        return failure_found, response, work_history

    async def _iterate_on_task(self, task: str, expected_answer: str) -> Tuple[str, None | str]:
        """
        Repeatedly assigns a task to the agent, and tries to learn from failures by creating useful insights as memories.
        """
        self.logger.enter_function()
        self.logger.info("\nTask description:  {}".format(task))
        self.logger.info("\nExpected answer:  {}\n".format(expected_answer))

        final_response = ""
        old_memos = await self.retrieve_relevant_memos(task)
        old_insights = [memo.insight for memo in old_memos]
        new_insights: List[str] = []
        last_insight = None
        insight = None
        successful_insight = None

        # Loop until success (or timeout) while learning from failures.
        for trial in range(1, self.max_train_trials + 1):
            self.logger.info("\n-----  TRAIN TRIAL {}  -----\n".format(trial))
            task_plus_insights = task

            # Add any new insights we've accumulated so far.
            if last_insight is not None:
                memory_section = self._format_memory_section(old_insights + [last_insight])
            else:
                memory_section = self._format_memory_section(old_insights)
            if len(memory_section) > 0:
                task_plus_insights += "\n\n" + memory_section

            # Can we find a failure case to learn from?
            failure_found, response, work_history = await self._test_for_failure(
                task, task_plus_insights, expected_answer
            )
            if not failure_found:
                # No. Time to exit the loop.
                self.logger.info("\nResponse is CORRECT.\n  Stop looking for insights.\n")
                # Was this the first trial?
                if trial == 1:
                    # Yes. We should return the successful response, and no insight.
                    final_response = response
                else:
                    # No. We learned a successful insight, which should be returned.
                    successful_insight = insight
                break

            # Will we try again?
            if trial == self.max_train_trials:
                # No. We're out of training trials.
                self.logger.info("\nNo more trials will be attempted.\n")
                break

            # Try to learn from this failure.
            self.logger.info("\nResponse is INCORRECT. Try to learn from this failure.\n")
            insight = await self.prompter.learn_from_failure(
                task, memory_section, response, expected_answer, work_history
            )
            self.logger.info("\nInsight:  {}\n".format(insight))
            new_insights.append(insight)
            last_insight = insight

        # Return the answer from the last loop.
        self.logger.info("\n{}\n".format(final_response))
        self.logger.leave_function()
        return final_response, successful_insight

    async def _append_any_relevant_memories(self, task: str) -> str:
        """
        Appends any relevant memories to the task description.
        """
        self.logger.enter_function()

        filtered_memos = await self.retrieve_relevant_memos(task)
        filtered_insights = [memo.insight for memo in filtered_memos]
        if len(filtered_insights) > 0:
            self.logger.info("Relevant insights were retrieved from memory.\n")
            memory_section = self._format_memory_section(filtered_insights)
            if len(memory_section) > 0:
                task = task + "\n\n" + memory_section

        self.logger.leave_function()
        return task

    async def assign_task(self, task: str, use_memory: bool = True, should_await: bool = True) -> str:
        """
        Assigns a task to some agent through the task_assignment_callback, along with any relevant memories.
        """
        self.logger.enter_function()

        assert self.task_assignment_callback is not None

        if use_memory:
            task = await self._append_any_relevant_memories(task)

        # Attempt to solve the task.
        self.logger.info("Try to solve the task.\n")
        assert should_await
        response, _ = await self.task_assignment_callback(task)

        self.logger.leave_function()
        return response

    async def consider_memo_storage(self, text: str) -> str | None:
        """
        Tries to extract any advice from the given text and add it to memory.
        """
        self.logger.enter_function()

        advice = await self.prompter.extract_advice(text)
        self.logger.info("Advice:  {}".format(advice))
        if advice is not None:
            await self.add_memo(insight=advice)

        self.logger.leave_function()
        return advice

    async def handle_user_message(self, text: str, should_await: bool = True) -> str:
        """
        Handles a user message by extracting any advice as an insight to be stored in memory, and then calling assign_task().
        """
        self.logger.enter_function()

        # Check for advice.
        advice = await self.consider_memo_storage(text)

        # Assign the task through the task_assignment_callback, using memory only if no advice was just provided.
        response = await self.assign_task(text, use_memory=(advice is None), should_await=should_await)

        self.logger.leave_function()
        return response
