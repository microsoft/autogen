import json
from typing import Any, Sequence, Tuple

from agnext.base import AgentId, AgentRuntime, MessageContext
from agnext.components import RoutedAgent, message_handler

from ..types import Reset, RespondNow, ResponseFormat, TextMessage

__all__ = ["OrchestratorChat"]


class OrchestratorChat(RoutedAgent):
    def __init__(
        self,
        description: str,
        runtime: AgentRuntime,
        orchestrator: AgentId,
        planner: AgentId,
        specialists: Sequence[AgentId],
        max_turns: int = 30,
        max_stalled_turns_before_retry: int = 2,
        max_retry_attempts: int = 1,
    ) -> None:
        super().__init__(description)
        self._orchestrator = orchestrator
        self._planner = planner
        self._specialists = specialists
        self._max_turns = max_turns
        self._max_stalled_turns_before_retry = max_stalled_turns_before_retry
        self._max_retry_attempts_before_educated_guess = max_retry_attempts

    @property
    def children(self) -> Sequence[AgentId]:
        return list(self._specialists) + [self._orchestrator, self._planner]

    @message_handler()
    async def on_text_message(
        self,
        message: TextMessage,
        ctx: MessageContext,
    ) -> TextMessage:
        # A task is received.
        task = message.content

        # Prepare the task.
        team, names, facts, plan = await self._prepare_task(task, message.source)

        # Main loop.
        total_turns = 0
        retry_attempts = 0
        while total_turns < self._max_turns:
            # Reset all agents.
            for agent in [*self._specialists, self._orchestrator]:
                await (await self.send_message(Reset(), agent))

            # Create the task specs.
            task_specs = f"""
We are working to address the following user request:

{task}


To answer this request we have assembled the following team:

{team}

Some additional points to consider:

{facts}

{plan}
""".strip()

            # Send the task specs to the orchestrator and specialists.
            for agent in [*self._specialists, self._orchestrator]:
                await (await self.send_message(TextMessage(content=task_specs, source=self.metadata["type"]), agent))

            # Inner loop.
            stalled_turns = 0
            while total_turns < self._max_turns:
                # Reflect on the task.
                data = await self._reflect_on_task(task, team, names, message.source)

                # Check if the request is satisfied.
                if data["is_request_satisfied"]["answer"]:
                    return TextMessage(
                        content=f"The task has been successfully addressed. {data['is_request_satisfied']['reason']}",
                        source=self.metadata["type"],
                    )

                # Update stalled turns.
                if data["is_progress_being_made"]["answer"]:
                    stalled_turns = max(0, stalled_turns - 1)
                else:
                    stalled_turns += 1

                # Handle retry.
                if stalled_turns > self._max_stalled_turns_before_retry:
                    # In a retry, we need to rewrite the facts and the plan.

                    # Rewrite the facts.
                    facts = await self._rewrite_facts(facts, message.source)

                    # Increment the retry attempts.
                    retry_attempts += 1

                    # Check if we should just guess.
                    if retry_attempts > self._max_retry_attempts_before_educated_guess:
                        # Make an educated guess.
                        educated_guess = await self._educated_guess(facts, message.source)
                        if educated_guess["has_educated_guesses"]["answer"]:
                            return TextMessage(
                                content=f"The task is addressed with an educated guess. {educated_guess['has_educated_guesses']['reason']}",
                                source=self.metadata["type"],
                            )

                    # Come up with a new plan.
                    plan = await self._rewrite_plan(team, message.source)

                    # Exit the inner loop.
                    break

                # Get the subtask.
                subtask = data["instruction_or_question"]["answer"]
                if subtask is None:
                    subtask = ""

                # Update agents.
                for agent in [*self._specialists, self._orchestrator]:
                    _ = await (
                        await self.send_message(
                            TextMessage(content=subtask, source=self.metadata["type"]),
                            agent,
                        )
                    )

                # Find the speaker.
                try:
                    speaker = next(agent for agent in self._specialists if agent.type == data["next_speaker"]["answer"])
                except StopIteration as e:
                    raise ValueError(f"Invalid next speaker: {data['next_speaker']['answer']}") from e

                # Ask speaker to speak.
                speaker_response = await (await self.send_message(RespondNow(), speaker))
                assert speaker_response is not None

                # Update all other agents with the speaker's response.
                for agent in [agent for agent in self._specialists if agent != speaker] + [self._orchestrator]:
                    await (
                        await self.send_message(
                            TextMessage(
                                content=speaker_response.content,
                                source=speaker_response.source,
                            ),
                            agent,
                        )
                    )

                # Increment the total turns.
                total_turns += 1

        return TextMessage(
            content="The task was not addressed. The maximum number of turns was reached.",
            source=self.metadata["type"],
        )

    async def _prepare_task(self, task: str, sender: str) -> Tuple[str, str, str, str]:
        # Reset planner.
        await (await self.send_message(Reset(), self._planner))

        # A reusable description of the team.
        team = "\n".join(
            [
                agent.type + ": " + (await self.runtime.agent_metadata(agent))["description"]
                for agent in self._specialists
            ]
        )
        names = ", ".join([agent.type for agent in self._specialists])

        # A place to store relevant facts.
        facts = ""

        # A plance to store the plan.
        plan = ""

        # Start by writing what we know
        closed_book_prompt = f"""Below I will present you a request. Before we begin addressing the request, please answer the following pre-survey to the best of your ability. Keep in mind that you are Ken Jennings-level with trivia, and Mensa-level with puzzles, so there should be a deep well to draw from.

Here is the request:

{task}

Here is the pre-survey:

    1. Please list any specific facts or figures that are GIVEN in the request itself. It is possible that there are none.
    2. Please list any facts that may need to be looked up, and WHERE SPECIFICALLY they might be found. In some cases, authoritative sources are mentioned in the request itself.
    3. Please list any facts that may need to be derived (e.g., via logical deduction, simulation, or computation)
    4. Please list any facts that are recalled from memory, hunches, well-reasoned guesses, etc.

When answering this survey, keep in mind that "facts" will typically be specific names, dates, statistics, etc. Your answer should use headings:

    1. GIVEN OR VERIFIED FACTS
    2. FACTS TO LOOK UP
    3. FACTS TO DERIVE
    4. EDUCATED GUESSES
""".strip()

        # Ask the planner to obtain prior knowledge about facts.
        await (await self.send_message(TextMessage(content=closed_book_prompt, source=sender), self._planner))
        facts_response = await (await self.send_message(RespondNow(), self._planner))

        facts = str(facts_response.content)

        # Make an initial plan
        plan_prompt = f"""Fantastic. To address this request we have assembled the following team:

{team}

Based on the team composition, and known and unknown facts, please devise a short bullet-point plan for addressing the original request. Remember, there is no requirement to involve all team members -- a team member's particular expertise may not be needed for this task.""".strip()

        # Send second messag eto the planner.
        await self.send_message(TextMessage(content=plan_prompt, source=sender), self._planner)
        plan_response = await (await self.send_message(RespondNow(), self._planner))
        plan = str(plan_response.content)

        return team, names, facts, plan

    async def _reflect_on_task(
        self,
        task: str,
        team: str,
        names: str,
        sender: str,
    ) -> Any:
        step_prompt = f"""
Recall we are working on the following request:

{task}

And we have assembled the following team:

{team}

To make progress on the request, please answer the following questions, including necessary reasoning:

    - Is the request fully satisfied? (True if complete, or False if the original request has yet to be SUCCESSFULLY addressed)
    - Are we making forward progress? (True if just starting, or recent messages are adding value. False if recent messages show evidence of being stuck in a reasoning or action loop, or there is evidence of significant barriers to success such as the inability to read from a required file)
    - Who should speak next? (select from: {names})
    - What instruction or question would you give this team member? (Phrase as if speaking directly to them, and include any specific information they may need)

Please output an answer in pure JSON format according to the following schema. The JSON object must be parsable as-is. DO NOT OUTPUT ANYTHING OTHER THAN JSON, AND DO NOT DEVIATE FROM THIS SCHEMA:

    {{
        "is_request_satisfied": {{
            "reason": string,
            "answer": boolean
        }},
        "is_progress_being_made": {{
            "reason": string,
            "answer": boolean
        }},
        "next_speaker": {{
            "reason": string,
            "answer": string (select from: {names})
        }},
        "instruction_or_question": {{
            "reason": string,
            "answer": string
        }}
    }}
""".strip()
        request = step_prompt
        while True:
            # Send a message to the orchestrator.
            await (await self.send_message(TextMessage(content=request, source=sender), self._orchestrator))
            # Request a response.
            step_response = await (
                await self.send_message(
                    RespondNow(response_format=ResponseFormat.json_object),
                    self._orchestrator,
                )
            )
            # TODO: use typed dictionary.
            try:
                result = json.loads(str(step_response.content))
            except json.JSONDecodeError as e:
                request = f"Invalid JSON: {str(e)}"
                continue
            if "is_request_satisfied" not in result:
                request = "Missing key: is_request_satisfied"
                continue
            elif (
                not isinstance(result["is_request_satisfied"], dict)
                or "answer" not in result["is_request_satisfied"]
                or "reason" not in result["is_request_satisfied"]
            ):
                request = "Invalid value for key: is_request_satisfied, expected 'answer' and 'reason'"
                continue
            if "is_progress_being_made" not in result:
                request = "Missing key: is_progress_being_made"
                continue
            elif (
                not isinstance(result["is_progress_being_made"], dict)
                or "answer" not in result["is_progress_being_made"]
                or "reason" not in result["is_progress_being_made"]
            ):
                request = "Invalid value for key: is_progress_being_made, expected 'answer' and 'reason'"
                continue
            if "next_speaker" not in result:
                request = "Missing key: next_speaker"
                continue
            elif (
                not isinstance(result["next_speaker"], dict)
                or "answer" not in result["next_speaker"]
                or "reason" not in result["next_speaker"]
            ):
                request = "Invalid value for key: next_speaker, expected 'answer' and 'reason'"
                continue
            elif result["next_speaker"]["answer"] not in names:
                request = f"Invalid value for key: next_speaker, expected 'answer' in {names}"
                continue
            if "instruction_or_question" not in result:
                request = "Missing key: instruction_or_question"
                continue
            elif (
                not isinstance(result["instruction_or_question"], dict)
                or "answer" not in result["instruction_or_question"]
                or "reason" not in result["instruction_or_question"]
            ):
                request = "Invalid value for key: instruction_or_question, expected 'answer' and 'reason'"
                continue
            return result

    async def _rewrite_facts(self, facts: str, sender: str) -> str:
        new_facts_prompt = f"""It's clear we aren't making as much progress as we would like, but we may have learned something new. Please rewrite the following fact sheet, updating it to include anything new we have learned. This is also a good time to update educated guesses (please add or update at least one educated guess or hunch, and explain your reasoning).

{facts}
""".strip()
        # Send a message to the orchestrator.
        await (await self.send_message(TextMessage(content=new_facts_prompt, source=sender), self._orchestrator))
        # Request a response.
        new_facts_response = await (await self.send_message(RespondNow(), self._orchestrator))
        return str(new_facts_response.content)

    async def _educated_guess(self, facts: str, sender: str) -> Any:
        # Make an educated guess.
        educated_guess_promt = f"""Given the following information

{facts}

Please answer the following question, including necessary reasoning:
    - Do you have two or more congruent pieces of information that will allow you to make an educated guess for the original request? The educated guess MUST answer the question.
Please output an answer in pure JSON format according to the following schema. The JSON object must be parsable as-is. DO NOT OUTPUT ANYTHING OTHER THAN JSON, AND DO NOT DEVIATE FROM THIS SCHEMA:

    {{
        "has_educated_guesses": {{
            "reason": string,
            "answer": boolean
        }}
    }}
""".strip()
        request = educated_guess_promt
        while True:
            # Send a message to the orchestrator.
            await (
                await self.send_message(
                    TextMessage(content=request, source=sender),
                    self._orchestrator,
                )
            )
            # Request a response.
            response = await (
                await self.send_message(
                    RespondNow(response_format=ResponseFormat.json_object),
                    self._orchestrator,
                )
            )
            try:
                result = json.loads(str(response.content))
            except json.JSONDecodeError as e:
                request = f"Invalid JSON: {str(e)}"
                continue
            # TODO: use typed dictionary.
            if "has_educated_guesses" not in result:
                request = "Missing key: has_educated_guesses"
                continue
            if (
                not isinstance(result["has_educated_guesses"], dict)
                or "answer" not in result["has_educated_guesses"]
                or "reason" not in result["has_educated_guesses"]
            ):
                request = "Invalid value for key: has_educated_guesses, expected 'answer' and 'reason'"
                continue
            return result

    async def _rewrite_plan(self, team: str, sender: str) -> str:
        new_plan_prompt = f"""Please come up with a new plan expressed in bullet points. Keep in mind the following team composition, and do not involve any other outside people in the plan -- we cannot contact anyone else.

Team membership:
{team}
""".strip()
        # Send a message to the orchestrator.
        await (await self.send_message(TextMessage(content=new_plan_prompt, source=sender), self._orchestrator))
        # Request a response.
        new_plan_response = await (await self.send_message(RespondNow(), self._orchestrator))
        return str(new_plan_response.content)
