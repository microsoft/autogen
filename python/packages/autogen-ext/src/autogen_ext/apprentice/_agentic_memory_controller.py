from typing import Callable, List
from ._prompter import Prompter
from ._agentic_memory_bank import AgenticMemoryBank
from ._grader import Grader


class AgenticMemoryController:
    def __init__(self, settings, agent, reset, client, logger):
        self.logger = logger
        self.logger.enter_function()

        self.settings = settings
        self.agent = agent
        self.client = client
        self.prompter = Prompter(client, logger)
        self.memory_bank = AgenticMemoryBank(self.settings["AgenticMemoryBank"],
                                             verbosity=3, reset=reset, logger=logger)
        self.grader = Grader(client, logger)

        self.logger.leave_function()

    def reset_memory(self):
        self.memory_bank.reset()

    async def train_on_task(self,
                            task: str,  # The task to be completed.
                            expected_answer: str,  # The expected answer to the task.
                            ):
        """
        Repeatedly assigns a task to the completion agent, and tries to learn from failures by creating useful insights as memories.
        """
        self.logger.enter_function()

        # Attempt to create useful new memories.
        self.logger.info("Iterate on the task, possibly discovering a useful new insight.\n")
        _, insight = await self._iterate_on_task(task, expected_answer,
            self.settings["max_train_trials"], self.settings["max_test_trials"])
        if insight is None:
            self.logger.info("No useful insight was discovered.\n")
        else:
            self.logger.info("A new insight was created:\n{}".format(insight))
            # Add this insight to memory.
            await self.add_insight_to_memory(task, insight)

        self.logger.leave_function()

    async def test_on_task(self, task: str, expected_answer: str, num_trials=1):
        """
        Assigns a task to the completion agent, along with any relevant insights/memories.
        """
        self.logger.enter_function()

        response = None
        num_successes = 0

        for trial in range(num_trials):
            self.logger.info("\n-----  TRIAL {}  -----\n".format(trial + 1))
            task_plus_insights = task

            # Try to retrieve any relevant memories from the DB.
            filtered_insights = await self.retrieve_relevant_insights(task)
            if len(filtered_insights) > 0:
                self.logger.info("Relevant insights were retrieved from memory.\n")
                memory_section = self.format_memory_section(filtered_insights)
                if len(memory_section) > 0:
                    task_plus_insights = task + '\n\n' + memory_section

            # Attempt to solve the task.
            self.logger.info("Try to solve the task.\n")
            response, _ = await self.agent.assign_task(task_plus_insights)

            response_is_correct, extracted_answer = await self.grader.is_response_correct(
                task, response, expected_answer)
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

    async def add_insight_to_memory(self, task: str, insight: str):
        # Adds an insight to the DB.
        self.logger.enter_function()

        self.logger.info("\nGIVEN TASK:")
        self.logger.info(task)

        self.logger.info("\nGIVEN INSIGHT:")
        self.logger.info(insight)

        # Generalize the task.
        generalized_task = await self.prompter.generalize_task(task)

        # Get a combined list of topics from the task and insight.
        task_plus_insight = generalized_task.strip() + "\n(Hint:  " + insight + ")"
        topics = await self.prompter.find_index_topics(task_plus_insight)
        self.logger.info("\nTOPICS EXTRACTED FROM TASK AND INSIGHT COMBINED:")
        self.logger.info("\n".join(topics))
        self.logger.info("")

        # Add the insight to the memory bank.
        self.memory_bank.add_insight(insight, generalized_task, topics)

        self.logger.leave_function()

    async def add_insight_without_task_to_memory(self, insight: str):
        # Adds an insight to the DB.
        self.logger.enter_function()

        self.logger.info("\nGIVEN INSIGHT:")
        self.logger.info(insight)

        # Get a list of topics from the insight.
        topics = await self.prompter.find_index_topics(insight)
        self.logger.info("\nTOPICS EXTRACTED FROM INSIGHT:")
        self.logger.info("\n".join(topics))
        self.logger.info("")

        # Add the insight to the memory bank.
        self.memory_bank.add_insight(insight, None, topics)

        self.logger.leave_function()

    async def retrieve_relevant_insights(self, task: str):
        # Retrieve insights from the DB that are relevant to the task.
        self.logger.enter_function()

        if self.memory_bank.contains_insights():
            self.logger.info("\nCURRENT TASK:")
            self.logger.info(task)

            # Generalize the task.
            generalized_task = await self.prompter.generalize_task(task)

            # Get a list of topics from the task.
            topics = await self.prompter.find_index_topics(generalized_task)
            self.logger.info("\nTOPICS EXTRACTED FROM TASK:")
            self.logger.info("\n".join(topics))
            self.logger.info("")

            # Retrieve relevant insights from the memory bank.
            relevant_insights_and_relevances = self.memory_bank.get_relevant_insights(topics=topics)
            relevant_insights = []
            self.logger.info("\n{} POTENTIALLY RELEVANT INSIGHTS".format(len(relevant_insights_and_relevances)))
            for insight, relevance in relevant_insights_and_relevances.items():
                self.logger.info("\n  INSIGHT: {}\n  RELEVANCE: {:.3f}".format(insight, relevance))
                relevant_insights.append(insight)

            # Apply a final validation stage to keep only the insights that the LLM concludes are relevant.
            validated_insights = []
            for insight in relevant_insights:
                if await self.prompter.validate_insight(insight, task):
                    validated_insights.append(insight)

            self.logger.info("\n{} VALIDATED INSIGHTS".format(len(validated_insights)))
            for insight in validated_insights:
                self.logger.info("\n  INSIGHT: {}".format(insight))
        else:
            self.logger.info("\nNO INSIGHTS WERE FOUND IN MEMORY")
            validated_insights = []

        self.logger.leave_function()
        return validated_insights

    def format_memory_section(self, memories):
        memory_section = ""
        if len(memories) > 0:
            memory_section = "## Important insights that may help solve tasks like this\n"
            for mem in memories:
                memory_section += ('- ' + mem + '\n')
        return memory_section

    async def _test_for_failure(self, task: str, task_plus_insights: str, expected_answer: str, num_trials: int):
        """
        Attempts to solve the given task multiple times to find a failure case to learn from.
        """
        self.logger.enter_function()

        self.logger.info("\nTask description, including any insights:  {}".format(task_plus_insights))
        self.logger.info("\nExpected answer:  {}\n".format(expected_answer))

        failure_found = False
        response, work_history = None, None

        for trial in range(num_trials):
            self.logger.info("\n-----  TRIAL {}  -----\n".format(trial + 1))

            # Attempt to solve the task.
            self.logger.info("Try to solve the task.")
            response, work_history = await self.agent.assign_task(task_plus_insights)

            response_is_correct, extracted_answer = await self.grader.is_response_correct(
                task, response, expected_answer)
            self.logger.info("Extracted answer:  {}".format(extracted_answer))
            if response_is_correct:
                self.logger.info("Answer is CORRECT.\n")
            else:
                self.logger.info("Answer is INCORRECT.\n  Stop testing, and return the details of the failure.\n")
                failure_found = True
                break

        self.logger.leave_function()
        return failure_found, response, work_history

    async def _iterate_on_task(self, task: str, expected_answer: str, max_train_trials: int, max_test_trials: int):
        self.logger.enter_function()

        self.logger.info("\nTask description:  {}".format(task))
        self.logger.info("\nExpected answer:  {}\n".format(expected_answer))

        final_response = None
        old_insights = await self.retrieve_relevant_insights(task)
        new_insights = []
        last_insight = None
        insight = None
        successful_insight = None

        # Loop until success (or timeout) while learning from failures.
        for trial in range(1, max_train_trials + 1):
            self.logger.info("\n-----  TRAIN TRIAL {}  -----\n".format(trial))

            task_plus_insights = task

            # Add any new insights we've accumulated so far.
            if last_insight is not None:
                memory_section = self.format_memory_section(old_insights + [last_insight])
            else:
                memory_section = self.format_memory_section(old_insights)
            if len(memory_section) > 0:
                task_plus_insights += '\n\n' + memory_section

            # Can we find a failure case to learn from?
            failure_found, response, work_history = await self._test_for_failure(
                task, task_plus_insights, expected_answer, max_test_trials)
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
            if trial == max_train_trials:
                # No. We're out of training trials.
                self.logger.info("\nNo more trials will be attempted.\n")
                break

            # Try to learn from this failure.
            self.logger.info("\nResponse is INCORRECT. Try to learn from this failure.\n")
            insight = await self.prompter.learn_from_failure(
                task, memory_section, response, expected_answer, work_history, new_insights)
            self.logger.info("\nInsight:  {}\n".format(insight))
            new_insights.append(insight)
            last_insight = insight

        # Return the answer from the last loop.
        self.logger.info("\n{}\n".format(final_response))
        self.logger.leave_function()
        return final_response, successful_insight

    async def assign_task(self, task: str, use_memory: bool = True, should_await: bool = True):
        """
        Assigns a task to the agent, along with any relevant insights/memories.
        """
        self.logger.enter_function()

        if use_memory:
            # Try to retrieve any relevant memories from the DB.
            filtered_insights = await self.retrieve_relevant_insights(task)
            if len(filtered_insights) > 0:
                self.logger.info("Relevant insights were retrieved from memory.\n")
                memory_section = self.format_memory_section(filtered_insights)
                task = task + '\n\n' + memory_section
                # if len(memory_section) > 0:  # Best to include this condition, but it will require new recordings.
                #     task = task + '\n\n' + memory_section

        # Attempt to solve the task.
        self.logger.info("Try to solve the task.\n")
        if should_await:
            response, _ = await self.agent.assign_task(task)
        else:
            response, _ = self.agent.assign_task(task)

        self.logger.leave_function()
        return response

    async def handle_user_message(self, text, should_await=True):
        self.logger.enter_function()

        advice = await self.prompter.extract_advice(text)
        self.logger.info("Advice:  {}".format(advice))

        if advice is not None:
            await self.add_insight_without_task_to_memory(advice)

        response = await self.assign_task(text, use_memory=(advice is None), should_await=should_await)

        self.logger.leave_function()
        return response

    async def learn_from_demonstration(self, task, demonstration):
        self.logger.enter_function()

        self.logger.info("\nEXAMPLE TASK:")
        self.logger.info(task)

        self.logger.info("\nEXAMPLE DEMONSTRATION:")
        self.logger.info(demonstration)

        # Get a list of topics from the task.
        topics = await self.prompter.find_index_topics(task.strip())
        self.logger.info("\nTOPICS EXTRACTED FROM TASK:")
        self.logger.info("\n".join(topics))
        self.logger.info("")

        # Add the insight to the memory bank.
        self.memory_bank.add_demonstration(task, demonstration, topics)

        self.logger.leave_function()
