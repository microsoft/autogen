import json
from typing import Any, Dict, List, Optional

from agnext.components.models import AssistantMessage, ChatCompletionClient, LLMMessage, SystemMessage, UserMessage
from agnext.core import AgentProxy

from ..messages import BroadcastMessage, OrchestrationEvent, ResetMessage
from .base_orchestrator import BaseOrchestrator, logger
from .orchestrator_prompts import (
    ORCHESTRATOR_CLOSED_BOOK_PROMPT,
    ORCHESTRATOR_LEDGER_PROMPT,
    ORCHESTRATOR_PLAN_PROMPT,
    ORCHESTRATOR_SYNTHESIZE_PROMPT,
    ORCHESTRATOR_SYSTEM_MESSAGE,
)


class RoundRobinOrchestrator(BaseOrchestrator):
    def __init__(
        self,
        agents: List[AgentProxy],
        description: str = "Round robin orchestrator",
        max_rounds: int = 20,
    ) -> None:
        super().__init__(agents=agents, description=description, max_rounds=max_rounds)

    async def _select_next_agent(self, message: LLMMessage) -> AgentProxy:
        self._current_index = (self._num_rounds) % len(self._agents)
        return self._agents[self._current_index]


class LedgerOrchestrator(BaseOrchestrator):
    DEFAULT_SYSTEM_MESSAGES = [
        SystemMessage(ORCHESTRATOR_SYSTEM_MESSAGE),
    ]

    def __init__(
        self,
        agents: List[AgentProxy],
        model_client: ChatCompletionClient,
        description: str = "Ledger-based orchestrator",
        system_messages: List[SystemMessage] = DEFAULT_SYSTEM_MESSAGES,
        closed_book_prompt: str = ORCHESTRATOR_CLOSED_BOOK_PROMPT,
        plan_prompt: str = ORCHESTRATOR_PLAN_PROMPT,
        synthesize_prompt: str = ORCHESTRATOR_SYNTHESIZE_PROMPT,
        ledger_prompt: str = ORCHESTRATOR_LEDGER_PROMPT,
        max_rounds: int = 20,
        max_stalls_before_replan: int = 3,
        max_replans: int = 4,
    ) -> None:
        super().__init__(agents=agents, description=description, max_rounds=max_rounds)

        self._model_client = model_client

        # prompt-based parameters
        self._system_messages = system_messages
        self._closed_book_prompt = closed_book_prompt
        self._plan_prompt = plan_prompt
        self._synthesize_prompt = synthesize_prompt
        self._ledger_prompt = ledger_prompt

        self._chat_history: List[LLMMessage] = []
        self._should_replan = True
        self._max_stalls_before_replan = max_stalls_before_replan
        self._stall_counter = 0
        self._max_replans = max_replans
        self._replan_counter = 0
        self.task_str = ""

    def _get_closed_book_prompt(self, task: str) -> str:
        return self._closed_book_prompt.format(task=task)

    def _get_plan_prompt(self, task: str, team: str) -> str:
        return self._plan_prompt.format(task=task, team=team)

    def _get_synthesize_prompt(self, task: str, team: str, facts: str, plan: str) -> str:
        return self._synthesize_prompt.format(task=task, team=team, facts=facts, plan=plan)

    def _get_ledger_prompt(self, task: str, team: str, names: List[str]) -> str:
        return self._ledger_prompt.format(task=task, team=team, names=names)

    async def _get_team_description(self) -> str:
        team_description = ""
        for agent in self._agents:
            metadata = await agent.metadata
            name = metadata["type"]
            description = metadata["description"]
            team_description += f"{name}: {description}\n"
        return team_description

    async def _get_team_names(self) -> List[str]:
        return [(await agent.metadata)["type"] for agent in self._agents]

    def _set_task_str(self, message: LLMMessage) -> None:
        if len(self._chat_history) == 1:
            if isinstance(message.content, str):
                self.task_str = message.content
            else:
                for content in message.content:
                    if isinstance(content, str):
                        self.task_str += content + "\n"
                        break
        assert len(self.task_str) > 0

    def _needs_replan(self) -> bool:
        if len(self._chat_history) == 1:
            self._set_task_str(self._chat_history[0])
            return True

        if self._stall_counter > self._max_stalls_before_replan:
            return True

        return False

    async def _plan(self) -> str:
        team_description = await self._get_team_description()

        # 1. GATHER FACTS
        # create a closed book task and generate a response and update the chat history
        cb_task = self._get_closed_book_prompt(self.task_str)
        cb_user_message = UserMessage(
            content=cb_task, source=self.metadata["type"]
        )  # TODO: allow images in this message.
        cb_response = await self._model_client.create(self._system_messages + self._chat_history + [cb_user_message])
        facts = cb_response.content
        assert isinstance(facts, str)
        cb_assistant_message = AssistantMessage(content=facts, source=self.metadata["type"])

        # 2. CREATE A PLAN
        ## plan based on available information
        plan_task = self._get_plan_prompt(self.task_str, team_description)
        plan_user_message = UserMessage(
            content=plan_task, source=self.metadata["type"]
        )  # TODO: allow images in this message.
        plan_response = await self._model_client.create(
            self._system_messages + self._chat_history + [cb_assistant_message, plan_user_message]
        )
        plan = plan_response.content
        assert isinstance(plan, str)

        # SYNTHESIZE FACTS AND PLAN
        plan_str = self._get_synthesize_prompt(self.task_str, team_description, facts, plan)
        return plan_str

    async def update_ledger(self) -> Dict[str, Any]:
        max_json_retries = 10

        team_description = await self._get_team_description()
        names = await self._get_team_names()
        ledger_prompt = self._get_ledger_prompt(self.task_str, team_description, names)

        ledger_user_messages: List[LLMMessage] = [UserMessage(content=ledger_prompt, source=self.metadata["type"])]

        assert max_json_retries > 0
        for _ in range(max_json_retries):
            ledger_response = await self._model_client.create(
                self._system_messages + self._chat_history + ledger_user_messages,
                json_output=True,
            )
            ledger_str = ledger_response.content

            try:
                assert isinstance(ledger_str, str)
                ledger_dict: Dict[str, Any] = json.loads(ledger_str)
                required_keys = [
                    "next_speaker",
                    "instruction_or_question",
                    "is_request_satisfied",
                    "is_in_loop",
                    "is_progress_being_made",
                ]
                key_error = False
                for key in required_keys:
                    if key not in ledger_dict:
                        ledger_user_messages.append(AssistantMessage(content=ledger_str, source="self"))
                        ledger_user_messages.append(
                            UserMessage(content=f"KeyError: '{key}'", source=self.metadata["type"])
                        )
                        key_error = True
                        break
                    if "answer" not in ledger_dict[key]:
                        ledger_user_messages.append(AssistantMessage(content=ledger_str, source="self"))
                        ledger_user_messages.append(
                            UserMessage(content=f"KeyError: '{key}.answer'", source=self.metadata["type"])
                        )
                        key_error = True
                        break
                if key_error:
                    continue
                return ledger_dict
            except json.JSONDecodeError as e:
                logger.info(
                    OrchestrationEvent(
                        f"{self.metadata['type']} (error)",
                        f"Failed to parse ledger information: {ledger_str}",
                    )
                )
                raise e

        raise ValueError("Failed to parse ledger information after multiple retries.")

    async def _select_next_agent(self, message: LLMMessage) -> Optional[AgentProxy]:
        self._chat_history.append(message)

        self._should_replan = self._needs_replan()

        if self._should_replan:
            plan_str = await self._plan()
            plan_user_message = UserMessage(content=plan_str, source=self.metadata["type"])
            logger.info(
                OrchestrationEvent(
                    f"{self.metadata['type']} (thought)",
                    f"New plan:\n{plan_str}",
                )
            )

            # Reset
            self._chat_history = [self._chat_history[0]]
            await self.publish_message(ResetMessage())
            self._chat_history.append(plan_user_message)

        ledger_dict = await self.update_ledger()
        logger.info(
            OrchestrationEvent(
                f"{self.metadata['type']} (thought)",
                f"Updated Ledger:\n{json.dumps(ledger_dict, indent=2)}",
            )
        )

        if ledger_dict["is_request_satisfied"]["answer"] is True:
            logger.info(
                OrchestrationEvent(
                    f"{self.metadata['type']} (thought)",
                    "Request satisfied.",
                )
            )
            return None

        if ledger_dict["is_in_loop"]["answer"]:
            self._stall_counter += 1

            if self._stall_counter > self._max_stalls_before_replan:
                self._replan_counter += 1
                self._stall_counter = 0
                if self._replan_counter < self._max_replans:
                    logger.info(
                        OrchestrationEvent(
                            f"{self.metadata['type']} (thought)",
                            "Stalled.... Replanning...",
                        )
                    )
                    return await self._select_next_agent(message)
                else:
                    logger.info(
                        OrchestrationEvent(
                            f"{self.metadata['type']} (thought)",
                            "Replan counter exceeded... Terminating.",
                        )
                    )
                    return None

        next_agent_name = ledger_dict["next_speaker"]["answer"]
        for agent in self._agents:
            if (await agent.metadata)["type"] == next_agent_name:
                # broadcast a new message
                instruction = ledger_dict["instruction_or_question"]["answer"]
                user_message = UserMessage(content=instruction, source=self.metadata["type"])
                logger.info(OrchestrationEvent(f"{self.metadata['type']} (-> {next_agent_name})", instruction))
                await self.publish_message(BroadcastMessage(content=user_message, request_halt=False))
                return agent

        return None
