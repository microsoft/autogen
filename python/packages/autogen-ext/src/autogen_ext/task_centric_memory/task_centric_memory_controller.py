from typing import Any, Awaitable, Callable, Dict, List, Tuple

from autogen_core.models import (
    ChatCompletionClient,
)

from ._prompter import Prompter
from ._task_centric_memory_bank import Memo, TaskCentricMemoryBank
from .grader import Grader
from .page_logger import PageLogger


class TaskCentricMemoryController:
    """
    Manages memory-based learning, testing, and the flow of information to and from the memory bank.

    Args:
        reset: True to clear the memory bank before starting.
        client: The client to call the model.
        task_assignment_callback: The callback to assign a task to the agent.
        - config: An optional dict that can be used to override the following values:
            - max_train_trials: The maximum number of trials to attempt when training on a task.
            - max_test_trials: The maximum number of trials to attempt when testing on a task.
            - TaskCentricMemoryBank: A config dict passed to TaskCentricMemoryBank.
        logger: An optional logger. If None, a default logger will be created.

    Methods:
        reset_memory: Resets the memory bank.
        train_on_task: Repeatedly assigns a task to the agent, and tries to learn from failures by creating useful insights as memories.
        test_on_task: Assigns a task to the agent, along with any relevant insights retrieved from memory.
        add_memo: Adds one insight to the memory bank, using the task (if provided) as context.
        add_task_solution_pair_to_memory: Adds a task-solution pair to the memory bank, to be retrieved together later as a combined insight.
        retrieve_relevant_memos: Retrieves any memos from memory that seem relevant to the task.
        assign_task: Assigns a task to the agent, along with any relevant insights/memories.
        handle_user_message: Handles a user message, extracting any advice and assigning a task to the agent.
    """

    def __init__(
        self,
        reset: bool,
        client: ChatCompletionClient,
        task_assignment_callback: Callable[[str], Awaitable[Tuple[str, str]]] | None,
        config: Dict[str, Any] | None = None,
        logger: PageLogger | None = None,
    ) -> None:
        if logger is None:
            logger = PageLogger({"level": "DEBUG"})
        self.logger = logger
        self.logger.enter_function()

        # Assign default values that can be overridden by config.
        self.max_train_trials = 10
        self.max_test_trials = 3
        memory_bank_config = None

        if config is not None:
            # Apply any overrides from the config.
            for key in config:
                if key == "max_train_trials":
                    self.max_train_trials = config[key]
                elif key == "max_test_trials":
                    self.max_test_trials = config[key]
                elif key == "TaskCentricMemoryBank":
                    memory_bank_config = config[key]
                else:
                    self.logger.error('Unexpected item in config: ["{}"] = {}'.format(key, config[key]))

        self.client = client
        self.task_assignment_callback = task_assignment_callback
        self.prompter = Prompter(client, logger)
        self.memory_bank = TaskCentricMemoryBank(reset=reset, config=memory_bank_config, logger=logger)
        self.grader = Grader(client, logger)
        self.logger.leave_function()

    def reset_memory(self) -> None:
        """
        Resets the memory bank.
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
        Assigns a task to the agent, along with any relevant insights retrieved from memory.
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

    async def add_memo(self, insight: str, task: None | str = None) -> None:
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
            task_plus_insight = insight
            self.logger.info("\nTOPICS EXTRACTED FROM INSIGHT:")
        else:
            task_plus_insight = generalized_task.strip() + "\n(Hint:  " + insight + ")"
            self.logger.info("\nTOPICS EXTRACTED FROM TASK AND INSIGHT COMBINED:")
        topics = await self.prompter.find_index_topics(task_plus_insight)
        self.logger.info("\n".join(topics))
        self.logger.info("")

        # Add the insight to the memory bank.
        self.memory_bank.add_memo(insight, topics, task)
        self.logger.leave_function()

    async def add_task_solution_pair_to_memory(self, task: str, solution: str) -> None:
        """
        Adds a task-solution pair to the memory bank, to be retrieved together later as a combined insight.
        This is useful when the insight is a demonstration of how to solve a given type of task.
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

    async def assign_task(self, task: str, use_memory: bool = True, should_await: bool = True) -> str:
        """
        Assigns a task to the agent, along with any relevant insights/memories.
        """
        self.logger.enter_function()

        assert self.task_assignment_callback is not None

        if use_memory:
            # Try to retrieve any relevant memories from the DB.
            filtered_memos = await self.retrieve_relevant_memos(task)
            filtered_insights = [memo.insight for memo in filtered_memos]
            if len(filtered_insights) > 0:
                self.logger.info("Relevant insights were retrieved from memory.\n")
                memory_section = self._format_memory_section(filtered_insights)
                task = task + "\n\n" + memory_section
                # if len(memory_section) > 0:  # Best to include this condition at some point, with new recordings.
                #     task = task + '\n\n' + memory_section

        # Attempt to solve the task.
        self.logger.info("Try to solve the task.\n")
        assert should_await
        response, _ = await self.task_assignment_callback(task)

        self.logger.leave_function()
        return response

    async def handle_user_message(self, text: str, should_await: bool = True) -> str:
        """
        Handles a user message, extracting any advice and assigning a task to the agent.
        """
        self.logger.enter_function()

        advice = await self.prompter.extract_advice(text)
        self.logger.info("Advice:  {}".format(advice))

        if advice is not None:
            await self.add_memo(insight=advice)

        response = await self.assign_task(text, use_memory=(advice is None), should_await=should_await)

        self.logger.leave_function()
        return response
