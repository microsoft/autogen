from typing import Callable, List
from ._prompter import Prompter
from ._knowledge_archive import KnowledgeArchive
from ._grader import Grader


class AgenticMemory:
    def __init__(self, reset, client, page_log, memory_dir, run_subdir):
        self.client = client
        self.page_log = page_log
        self.prompter = Prompter(client, page_log)
        self.archive = KnowledgeArchive(verbosity=0, reset=reset, memory_dir=memory_dir, run_subdir=run_subdir,
                                        page_log=page_log)
        self.grader = Grader(client, page_log)

    async def train_on_task(self,
                            task: str,  # The task to be completed.
                            expected_answer: str,  # The expected answer to the task.
                            task_assignment_callback: Callable,  # The function through which to assign the task.
                            final_format_instructions: str,  # Instructions for formatting the final response, if any.
                            max_train_trials: int,  # The maximum number of training trials to attempt.
                            max_test_trials: int,  # The number of successful test trials to qualify as success.
                            ):
        """
        Repeatedly assigns a task to the completion agent, and tries to learn from failures by creating useful insights as memories.
        """
        page = self.page_log.begin_page(
            summary="AgenticMemory.train_on_task",
            details="",
            method_call="AgenticMemory.train_on_task")

        # Attempt to create useful new memories.
        page.add_lines("Iterate on the task, possibly discovering a useful new insight.\n", flush=True)
        _, insight = await self._iterate_on_task(task, expected_answer, task_assignment_callback,
                                                final_format_instructions, max_train_trials, max_test_trials)
        if insight is None:
            page.add_lines("No useful insight was discovered.\n", flush=True)
        else:
            page.add_lines("A new insight was created:\n{}".format(insight), flush=True)
            # Add this insight to memory.
            await self.add_insight_to_memory(task, insight)

        self.page_log.finish_page(page)

    async def test_on_task(self, task: str, expected_answer: str, task_assignment_callback: Callable, num_trials=1):
        """
        Assigns a task to the completion agent, along with any relevant insights/memories.
        """
        page = self.page_log.begin_page(
            summary="AgenticMemory.test_on_task",
            details="",
            method_call="AgenticMemory.test_on_task")

        response = None
        num_successes = 0

        for trial in range(num_trials):
            page.add_lines("\n-----  TRIAL {}  -----\n".format(trial + 1), flush=True)
            task_plus_insights = task

            # Try to retrieve any relevant memories from the DB.
            filtered_insights = await self.retrieve_relevant_insights(task)
            if len(filtered_insights) > 0:
                page.add_lines("Relevant insights were retrieved from memory.\n", flush=True)
                memory_section = self.format_memory_section(filtered_insights)
                if len(memory_section) > 0:
                    task_plus_insights = task + '\n\n' + memory_section

            # Attempt to solve the task.
            page.add_lines("Try to solve the task.\n", flush=True)
            response, _ = await task_assignment_callback(task_plus_insights, self.client, self.page_log)

            response_is_correct, extracted_answer = await self.grader.response_is_correct(
                task, response, expected_answer)
            page.add_lines("Extracted answer:  {}".format(extracted_answer), flush=True)
            if response_is_correct:
                page.add_lines("Answer is CORRECT.\n", flush=True)
                num_successes += 1
            else:
                page.add_lines("Answer is INCORRECT.\n", flush=True)

        # Calculate the success rate as a percentage, rounded to the nearest whole number.
        page.add_lines("\nSuccess rate:  {}%\n".format(round((num_successes / num_trials) * 100)), flush=True)

        self.page_log.finish_page(page)
        return response, num_successes, num_trials

    async def add_insight_to_memory(self, task: str, insight: str):
        # Adds an insight to the DB.
        page = self.page_log.begin_page(
            summary="AgenticMemory.add_insight_to_memory",
            details="",
            method_call="AgenticMemory.add_insight_to_memory")

        page.add_lines("\nGIVEN TASK:")
        page.add_lines(task)

        page.add_lines("\nGIVEN INSIGHT:")
        page.add_lines(insight)

        # Generalize the task.
        generalized_task = await self.prompter.generalize_task(task)

        # Get a combined list of topics from the task and insight.
        task_plus_insight = generalized_task.strip() + "\n(Hint:  " + insight + ")"
        topics = await self.prompter.find_index_topics(task_plus_insight)
        page.add_lines("\nTOPICS EXTRACTED FROM TASK AND INSIGHT COMBINED:")
        page.add_lines("\n".join(topics))
        page.add_lines("")

        # Add the insight to the archive.
        self.archive.add_insight(insight, generalized_task, topics)

        self.page_log.finish_page(page)

    async def add_insight_without_task_to_memory(self, insight: str):
        # Adds an insight to the DB.
        page = self.page_log.begin_page(
            summary="AgenticMemory.add_insight_without_task_to_memory",
            details="",
            method_call="AgenticMemory.add_insight_without_task_to_memory")

        page.add_lines("\nGIVEN INSIGHT:")
        page.add_lines(insight)

        # Get a list of topics from the insight.
        topics = await self.prompter.find_index_topics(insight)
        page.add_lines("\nTOPICS EXTRACTED FROM INSIGHT:")
        page.add_lines("\n".join(topics))
        page.add_lines("")

        # Add the insight to the archive.
        self.archive.add_insight(insight, None, topics)

        self.page_log.finish_page(page)

    async def retrieve_relevant_insights(self, task: str):
        # Retrieve insights from the DB that are relevant to the task.
        page = self.page_log.begin_page(
            summary="AgenticMemory.retrieve_relevant_insights",
            details="",
            method_call="AgenticMemory.retrieve_relevant_insights")

        page.add_lines("\nCURRENT TASK:")
        page.add_lines(task)

        # Generalize the task.
        generalized_task = await self.prompter.generalize_task(task)

        # Get a list of topics from the task.
        topics = await self.prompter.find_index_topics(generalized_task)
        page.add_lines("\nTOPICS EXTRACTED FROM TASK:")
        page.add_lines("\n".join(topics))
        page.add_lines("")

        # Retrieve relevant insights from the archive.
        relevant_insights_and_relevances = self.archive.get_relevant_insights(topics=topics)
        relevant_insights = []
        page.add_lines("\n{} POTENTIALLY RELEVANT INSIGHTS".format(len(relevant_insights_and_relevances)))
        for insight, relevance in relevant_insights_and_relevances.items():
            page.add_lines("\n  INSIGHT: {}\n  RELEVANCE: {:.3f}".format(insight, relevance))
            relevant_insights.append(insight)

        validated_insights = []
        if len(relevant_insights) > 0:
            # Apply a final validation stage to keep only the insights that the LLM concludes are relevant.
            validated_insights = await self.prompter.validate_insights(relevant_insights, task)
        page.add_lines("\n{} VALIDATED INSIGHTS".format(len(validated_insights)))
        for insight in validated_insights:
            page.add_lines("\n  INSIGHT: {}".format(insight))

        self.page_log.finish_page(page)
        return validated_insights

    def format_memory_section(self, memories):
        memory_section = ""
        if len(memories) > 0:
            memory_section = "## Important insights that may help solve tasks like this\n"
            for mem in memories:
                memory_section += ('- ' + mem + '\n')
        return memory_section

    async def _test_for_failure(self, task: str, task_plus_insights: str, expected_answer: str,
                                assign_task_to_completer: Callable, num_trials: int):
        """
        Attempts to solve the given task multiple times to find a failure case to learn from.
        """
        page = self.page_log.begin_page(
            summary="AgenticMemory._test_for_failure",
            details="",
            method_call="AgenticMemory._test_for_failure")

        page.add_lines("\nTask description, including any insights:  {}".format(task_plus_insights))
        page.add_lines("\nExpected answer:  {}\n".format(expected_answer))

        failure_found = False
        response, work_history = None, None

        for trial in range(num_trials):
            page.add_lines("\n-----  TRIAL {}  -----\n".format(trial + 1), flush=True)

            # Attempt to solve the task.
            page.add_lines("Try to solve the task.", flush=True)
            response, work_history = await assign_task_to_completer(task_plus_insights, self.client, self.page_log)

            response_is_correct, extracted_answer = await self.grader.response_is_correct(
                task, response, expected_answer)
            page.add_lines("Extracted answer:  {}".format(extracted_answer), flush=True)
            if response_is_correct:
                page.add_lines("Answer is CORRECT.\n", flush=True)
            else:
                page.add_lines("Answer is INCORRECT.\n  Stop testing, and return the details of the failure.\n", flush=True)
                failure_found = True
                break

        self.page_log.finish_page(page)
        return failure_found, response, work_history

    async def _iterate_on_task(self, task: str, expected_answer: str, assign_task_to_completer: Callable,
                              final_format_instructions: str, max_train_trials: int, max_test_trials: int):
        page = self.page_log.begin_page(
            summary="AgenticMemory._iterate_on_task",
            details="",
            method_call="AgenticMemory._iterate_on_task")

        page.add_lines("\nTask description:  {}".format(task))
        page.add_lines("\nExpected answer:  {}\n".format(expected_answer))

        final_response = None
        old_insights = await self.retrieve_relevant_insights(task)
        new_insights = []
        last_insight = None
        insight = None
        successful_insight = None

        # Loop until success (or timeout) while learning from failures.
        for trial in range(1, max_train_trials + 1):
            page.add_lines("\n-----  TRAIN TRIAL {}  -----\n".format(trial), flush=True)

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
                task, task_plus_insights, expected_answer, assign_task_to_completer, max_test_trials)
            if not failure_found:
                # No. Time to exit the loop.
                page.add_lines("\nResponse is CORRECT.\n  Stop looking for insights.\n", flush=True)
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
                page.add_lines("\nNo more trials will be attempted.\n", flush=True)
                break

            # Try to learn from this failure.
            page.add_lines("\nResponse is INCORRECT. Try to learn from this failure.\n", flush=True)
            insight = await self.prompter.learn_from_failure(
                task, memory_section, response, expected_answer, work_history, final_format_instructions, new_insights)
            page.add_lines("\nInsight:  {}\n".format(insight), flush=True)
            new_insights.append(insight)
            last_insight = insight

        # Return the answer from the last loop.
        page.add_lines("\n{}\n".format(final_response), flush=True)
        self.page_log.finish_page(page)
        return final_response, successful_insight

    async def execute_task(self, task: str, task_assignment_callback: Callable, should_await: bool,
                           should_retrieve_insights: bool = True):
        """
        Assigns a task to the completion agent, along with any relevant insights/memories.
        """
        page = self.page_log.begin_page(
            summary="AgenticMemory.execute_task",
            details="",
            method_call="AgenticMemory.execute_task")

        if should_retrieve_insights:
            # Try to retrieve any relevant memories from the DB.
            filtered_insights = await self.retrieve_relevant_insights(task)
            if len(filtered_insights) > 0:
                page.add_lines("Relevant insights were retrieved from memory.\n", flush=True)
                memory_section = self.format_memory_section(filtered_insights)
                task = task + '\n\n' + memory_section

        # Attempt to solve the task.
        page.add_lines("Try to solve the task.\n", flush=True)
        if should_await:
            response, _ = await task_assignment_callback(task, self.client, self.page_log)
        else:
            response, _ = task_assignment_callback(task, self.client, self.page_log)

        # page.add_lines("Response:  {}\n".format(response), flush=True)

        self.page_log.finish_page(page)
        return response

    async def handle_user_message(self, text, task_assignment_callback, should_await=True):
        page = self.page_log.begin_page(
            summary="AgenticMemory.handle_user_message",
            details="",
            method_call="AgenticMemory.handle_user_message")

        # task = await self.prompter.extract_task(text)
        # page.add_lines("Task:  {}".format(task), flush=True)

        advice = await self.prompter.extract_advice(text)
        page.add_lines("Advice:  {}".format(advice), flush=True)

        if advice is not None:
            print("Adding advice to memory.")
            await self.add_insight_without_task_to_memory(advice)

        print("Passing task to completion agent.")
        response = await self.execute_task(text, task_assignment_callback, should_await,
                                           should_retrieve_insights=(advice is None))

        self.page_log.finish_page(page)
        return response

    async def learn_from_demonstration(self, task, demonstration):
        page = self.page_log.begin_page(
            summary="AgenticMemory.learn_from_demonstration",
            details="",
            method_call="AgenticMemory.learn_from_demonstration")

        page.add_lines("\nEXAMPLE TASK:")
        page.add_lines(task)

        page.add_lines("\nEXAMPLE DEMONSTRATION:")
        page.add_lines(demonstration)

        # Get a list of topics from the task.
        topics = await self.prompter.find_index_topics(task.strip())
        page.add_lines("\nTOPICS EXTRACTED FROM TASK:")
        page.add_lines("\n".join(topics))
        page.add_lines("")

        # Add the insight to the archive.
        self.archive.add_demonstration(task, demonstration, topics)

        self.page_log.finish_page(page)
