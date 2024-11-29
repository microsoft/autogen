from typing import Callable
from ._prompter import Prompter
from ._knowledge_archive import KnowledgeArchive


class AgenticMemory:
    def __init__(self, reset, client, page_log, path_to_archive_dir):
        self.client = client
        self.page_log = page_log
        self.prompter = Prompter(client, page_log)
        self.archive = KnowledgeArchive(verbosity=0, reset=reset, path_to_archive_dir=path_to_archive_dir,
                                        page_log=page_log)

    async def assign_task(self, task: str, expected_answer: str, create_new_memories: bool, assign_task_to_completer: Callable,
                          final_format_instructions: str):
        """
        Assigns a task to the completion agent, using any relevant memories, and tries to learn from failures.
        If the first attempt succeeds, that response is returned without attempting to learn.
        """
        page = self.page_log.begin_page(
            summary="AgenticMemory.assign_task",
            details="",
            method_call="AgenticMemory.assign_task")

        if create_new_memories:
            page.add_lines("Iterate on the task, possibly discovering a useful new insight.\n", flush=True)
            # Attempt to create useful new memories.
            _, insight = await self.iterate_on_task(task, expected_answer, assign_task_to_completer, final_format_instructions)
            if insight is not None:
                page.add_lines("A new insight was created:\n{}".format(insight), flush=True)
                # Add this insight to memory.
                await self.add_insight_to_memory(task, insight)

        # Retrieve insights from memory.
        filtered_insights = await self.retrieve_relevant_insights(task)

        # Try to solve the task, looking up relevant memories from the DB.
        page.add_lines("Try to solve the task, using any insights from the db.\n", flush=True)
        if len(filtered_insights) > 0:
            page.add_lines("Relevant insights were found in memory.\n", flush=True)
            memory_section = self.format_memory_section(filtered_insights)
            task = task + '\n\n' + memory_section

        # Attempt to solve the task.
        final_response, _ = await assign_task_to_completer(task, self.client, self.page_log)

        page.add_lines("\n{}\n".format(final_response), flush=True)
        self.page_log.finish_page(page)
        return final_response

    async def add_insight_to_memory(self, task: str, insight: str):
        # Adds an insight to the DB.
        page = self.page_log.begin_page(
            summary="AgenticMemory.add_insight_to_memory",
            details="",
            method_call="AgenticMemory.add_insight_to_memory")

        # Get a combined list of topics from the task and insight.
        task_plus_insight = task.strip() + "\n(Hint:  " + insight + ")"
        topics = await self.prompter.find_index_topics(task_plus_insight)
        page.add_lines("\nTOPICS EXTRACTED FROM TASK AND INSIGHT:")
        page.add_lines("\n".join(topics))
        page.add_lines("")

        # Add the insight to the archive.
        self.archive.add_insight(insight, task, topics)

        self.page_log.finish_page(page)

    async def retrieve_relevant_insights(self, task: str):
        # Retrieve insights from the DB that are relevant to the task.
        page = self.page_log.begin_page(
            summary="AgenticMemory.retrieve_relevant_insights",
            details="",
            method_call="AgenticMemory.retrieve_relevant_insights")

        # Get a list of topics from the task.
        topics = await self.prompter.find_index_topics(task)
        page.add_lines("\nTOPICS EXTRACTED FROM TASK:")
        page.add_lines("\n".join(topics))
        page.add_lines("")

        # Retrieve insights from the archive.
        unfiltered_insights = self.archive.get_relevant_insights(topics=topics)
        filtered_insights = []
        page.add_lines("\nUNFILTERED INSIGHTS")
        for insight, relevance in unfiltered_insights.items():
            page.add_lines("  INSIGHT: {}\n  RELEVANCE: {:.3f}".format(insight, relevance))
            if relevance > 5.0:
                filtered_insights.append(insight)
        page.add_lines("\nFiltered to top {} insights".format(len(filtered_insights)))

        self.page_log.finish_page(page)
        return filtered_insights

    def format_memory_section(self, memories):
        memory_section = ""
        if len(memories) > 0:
            memory_section = "## Important insights that may help solve tasks like this\n"
            for mem in memories:
                memory_section += ('- ' + mem + '\n')
        return memory_section

    async def iterate_on_task(self, task: str, expected_answer: str, assign_task_to_completer: Callable, final_format_instructions: str):
        page = self.page_log.begin_page(
            summary="AgenticMemory.iterate_on_task",
            details="",
            method_call="AgenticMemory.iterate_on_task")

        page.add_lines("\nTask description:  {}".format(task))
        page.add_lines("\nExpected answer:  {}\n".format(expected_answer))

        final_response = None
        old_insights = await self.retrieve_relevant_insights(task)
        new_insights = []
        insight = None
        successful_insight = None

        # Loop until success (or timeout) while learning from failures.
        max_trials = 4
        for trial in range(1, max_trials + 1):
            page.add_lines("-----  TRIAL {}  -----\n".format(trial), flush=True)

            # Add any new insights we've accumulated so far.
            memory_section = self.format_memory_section(old_insights + new_insights)
            task_plus_insights = task + '\n\n' + memory_section

            # Attempt to solve the task.
            response, work_history = await assign_task_to_completer(task_plus_insights, self.client, self.page_log)

            # Is this answer correct?
            page.add_lines("\nResponse:  {}".format(response), flush=True)
            response_is_correct = (response.lower() == expected_answer.lower())
            if response_is_correct:
                # Yes. Time to exit the loop.
                page.add_lines("\nResponse is CORRECT. No learning needed.\n", flush=True)
                # Was this the first trial?
                if trial == 1:
                    # Yes. We should return the successful response, and no insight.
                    final_response = response
                else:
                    # No. We learned a successful insight, which should be returned.
                    successful_insight = insight
                break

            # Will we try again?
            if trial == max_trials:
                # No. We're out of tries.
                page.add_lines("\nNo more trials will be attempted.\n", flush=True)
                break

            # Try to learn from this failure.
            page.add_lines("\nResponse is INCORRECT. Try to learn from this failure.\n", flush=True)
            insight = await self.prompter.learn_from_failure(
                task, memory_section, response, expected_answer, work_history, final_format_instructions)
            page.add_lines("\nInsight:  {}\n".format(insight), flush=True)
            new_insights.append(insight)

        # Return the answer from the last loop.
        page.add_lines("\n{}\n".format(final_response), flush=True)
        self.page_log.finish_page(page)
        return final_response, successful_insight
