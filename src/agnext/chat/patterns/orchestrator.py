import json
from typing import Any, List, Sequence, Tuple

from ...agent_components.model_client import ModelClient
from ...agent_components.type_routed_agent import TypeRoutedAgent, message_handler
from ...agent_components.types import AssistantMessage, LLMMessage, UserMessage
from ...core.agent_runtime import AgentRuntime
from ...core.cancellation_token import CancellationToken
from ..agents.base import BaseChatAgent
from ..messages import ChatMessage


class Orchestrator(BaseChatAgent, TypeRoutedAgent):
    def __init__(
        self,
        name: str,
        description: str,
        runtime: AgentRuntime,
        agents: Sequence[BaseChatAgent],
        model_client: ModelClient,
        max_turns: int = 30,
        max_stalled_turns_before_retry: int = 2,
        max_retry_attempts: int = 1,
    ) -> None:
        super().__init__(name, description, runtime)
        self._agents = agents
        self._model_client = model_client
        self._max_turns = max_turns
        self._max_stalled_turns_before_retry = max_stalled_turns_before_retry
        self._max_retry_attempts_before_educated_guess = max_retry_attempts
        self._history: List[ChatMessage] = []

    @message_handler(ChatMessage)
    async def on_chat_message(
        self,
        message: ChatMessage,
        require_response: bool,
        cancellation_token: CancellationToken,
    ) -> ChatMessage | None:
        # A task is received.
        task = message.body

        if message.reset:
            # Reset the history.
            self._history = []
        if message.save_message_only:
            # TODO: what should we do with save_message_only messages for this pattern?
            return ChatMessage(body="OK", sender=self.name)

        # Prepare the task.
        team, names, facts, plan = await self._prepare_task(task, message.sender)

        # Main loop.
        total_turns = 0
        retry_attempts = 0
        ledgers: List[List[LLMMessage]] = []
        while total_turns < self._max_turns:
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

            # Send the task specs to the team and signal a reset.
            for agent in self._agents:
                self._send_message(
                    ChatMessage(
                        body=task_specs,
                        sender=self.name,
                        save_message_only=True,
                        reset=True,
                    ),
                    agent,
                )

            # Create the ledger.
            ledger: List[LLMMessage] = [
                AssistantMessage(
                    content=task_specs,
                    source=self.name,
                )
            ]
            ledgers.append(ledger)

            # Inner loop.
            stalled_turns = 0
            while total_turns < self._max_turns:
                # Reflect on the task.
                data = await self._reflect_on_task(task, team, names, ledger, message.sender)

                # Check if the request is satisfied.
                if data["is_request_satisfied"]["answer"]:
                    return ChatMessage(
                        body="The task has been successfully addressed.",
                        sender=self.name,
                        payload={
                            "ledgers": ledgers,
                            "status": "success",
                            "reason": data["is_request_satisfied"]["reason"],
                        },
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
                    facts = await self._rewrite_facts(facts, ledger, message.sender)

                    # Increment the retry attempts.
                    retry_attempts += 1

                    # Check if we should just guess.
                    if retry_attempts > self._max_retry_attempts_before_educated_guess:
                        # Make an educated guess.
                        educated_guess = await self._educated_guess(facts, ledger, message.sender)
                        if educated_guess["has_educated_guesses"]["answer"]:
                            return ChatMessage(
                                body="The task is addressed with an educated guess.",
                                sender=self.name,
                                payload={
                                    "ledgers": ledgers,
                                    "status": "educated_guess",
                                    "reason": educated_guess["has_educated_guesses"]["reason"],
                                },
                            )

                    # Come up with a new plan.
                    plan = await self._rewrite_plan(team, ledger, message.sender)

                    # Exit the inner loop.
                    break

                # Get the subtask.
                subtask = data["instruction_or_question"]["answer"]
                if subtask is None:
                    subtask = ""

                # Find the speaker.
                try:
                    speaker = next(agent for agent in self._agents if agent.name == data["next_speaker"]["answer"])
                except StopIteration as e:
                    raise ValueError(f"Invalid next speaker: {data['next_speaker']['answer']}") from e

                # Update all other agents.
                for agent in [agent for agent in self._agents if agent != speaker]:
                    _ = await self._send_message(
                        ChatMessage(
                            body=subtask,
                            sender=self.name,
                            save_message_only=True,
                        ),
                        agent,
                    )

                # Update the speaker and ask to speak.
                speaker_response = await self._send_message(
                    ChatMessage(body=subtask, sender=self.name),
                    speaker,
                )

                assert speaker_response is not None

                # Update the ledger.
                ledger.append(
                    AssistantMessage(
                        content=subtask,
                        source=self.name,
                    )
                )

                # Update all other agents with the speaker's response.
                for agent in [agent for agent in self._agents if agent != speaker]:
                    _ = await self._send_message(
                        ChatMessage(
                            body=speaker_response.body,
                            sender=speaker_response.sender,
                            save_message_only=True,
                        ),
                        agent,
                    )

                # Update the ledger.
                ledger.append(
                    UserMessage(
                        content=speaker_response.body,
                        source=speaker_response.sender,
                    )
                )

                # Increment the total turns.
                total_turns += 1

        return ChatMessage(
            body="The task was not addressed",
            sender=self.name,
            payload={
                "ledgers": ledgers,
                "status": "failure",
                "reason": "The maximum number of turns was reached.",
            },
        )

    async def _prepare_task(self, task: str, sender: str) -> Tuple[str, str, str, str]:
        # A reusable description of the team.
        team = "\n".join([agent.name + ": " + agent.description for agent in self._agents])
        names = ", ".join([agent.name for agent in self._agents])

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

        starter_messages: List[LLMMessage] = [
            UserMessage(
                content=closed_book_prompt,
                source=sender,
            )
        ]
        facts_response = await self._model_client.create(messages=starter_messages)
        starter_messages.append(
            AssistantMessage(
                content=facts_response.content,
                source=self.name,
            )
        )
        facts = str(facts_response.content)

        # Make an initial plan
        plan_prompt = f"""Fantastic. To address this request we have assembled the following team:

{team}

Based on the team composition, and known and unknown facts, please devise a short bullet-point plan for addressing the original request. Remember, there is no requirement to involve all team members -- a team member's particular expertise may not be needed for this task.""".strip()
        starter_messages.append(
            UserMessage(
                content=plan_prompt,
                source=sender,
            )
        )
        plan_response = await self._model_client.create(messages=starter_messages)
        starter_messages.append(
            AssistantMessage(
                content=plan_response.content,
                source=self.name,
            )
        )
        plan = str(plan_response.content)

        return team, names, facts, plan

    async def _reflect_on_task(
        self,
        task: str,
        team: str,
        names: str,
        ledger: List[LLMMessage],
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
        step_response = await self._model_client.create(
            messages=ledger + [UserMessage(content=step_prompt, source=sender)],
            extra_create_args={"response_format": {"type": "json_object"}},
        )
        step_response_json = str(step_response.content)
        # TODO: handle invalid JSON.
        # TODO: use typed dictionary.
        return json.loads(step_response_json)

    async def _rewrite_facts(self, facts: str, ledger: List[LLMMessage], sender: str) -> str:
        new_facts_prompt = f"""It's clear we aren't making as much progress as we would like, but we may have learned something new. Please rewrite the following fact sheet, updating it to include anything new we have learned. This is also a good time to update educated guesses (please add or update at least one educated guess or hunch, and explain your reasoning).

{facts}
""".strip()
        ledger.append(
            UserMessage(
                content=new_facts_prompt,
                source=sender,
            )
        )
        new_facts_response = await self._model_client.create(messages=ledger)
        facts = str(new_facts_response.content)
        ledger.append(
            AssistantMessage(
                content=facts,
                source=self.name,
            )
        )
        return facts

    async def _educated_guess(self, facts: str, ledger: List[LLMMessage], sender: str) -> Any:
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
        educated_guess_response = await self._model_client.create(
            messages=ledger + [UserMessage(content=educated_guess_promt, source=sender)],
            extra_create_args={"response_format": {"type": "json_object"}},
        )
        # TODO: handle invalid JSON.
        # TODO: use typed dictionary.
        return json.loads(str(educated_guess_response.content))

    async def _rewrite_plan(self, team: str, ledger: List[LLMMessage], sender: str) -> str:
        new_plan_prompt = f"""Please come up with a new plan expressed in bullet points. Keep in mind the following team composition, and do not involve any other outside people in the plan -- we cannot contact anyone else.

Team membership:
{team}
""".strip()
        ledger.append(
            UserMessage(
                content=new_plan_prompt,
                source=sender,
            )
        )
        new_plan_response = await self._model_client.create(messages=ledger)
        return str(new_plan_response.content)
