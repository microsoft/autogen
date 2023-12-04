from collections import defaultdict
import openai
import json
import time
import logging
from typing import Dict, Optional, Union, List, Tuple, Any

from autogen.agentchat.agent import Agent
from autogen.agentchat.assistant_agent import ConversableAgent

try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x


logger = logging.getLogger(__name__)


class StrategistAgent(ConversableAgent):
    """(In preview) StrategistAgent is an agent that dispatches messages to other agents."""

    def __init__(
        self,
        name: Optional[str] = "manager",
        agents: Optional[List[Agent]] = None,
        human_input_mode: Optional[str] = "ALWAYS",
        llm_config: Optional[Union[Dict, bool]] = None,
        system_message: Optional[
            Union[str, List]
        ] = "Planner. Structure your approach by breaking down the query into smaller, manageable sub-problems and dispatching them to the appropriate agents.",
        **kwargs,
    ):
        if agents is None:
            raise ValueError("agents must be provided. StrategistAgent needs agents to implement actions")

        self.agents = agents
        self._llm_config = llm_config.copy() if llm_config is not None else {}
        functions = self._llm_config.get("functions", [])
        functions.extend([ag.as_function_call_schema() for ag in agents])
        self._llm_config["functions"] = functions

        super().__init__(
            name=name,
            human_input_mode=human_input_mode,
            system_message=system_message,
            llm_config=self._llm_config,
            **kwargs,
        )

        self.register_reply(Agent, StrategistAgent.dispatching)
        self.register_reply(Agent, StrategistAgent.a_dispatching)

    def dispatching(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ) -> Union[str, Dict, None]:
        """
        Dispatches messages to the appropriate agents.
        If there is no agent that can handle the message, fallback to manual mode.
        """
        final, response = self.generate_oai_reply(messages, sender, config)
        if not final:
            return True, f"{self.name} is not available now, please try again."

        message = self._message_to_dict(response)
        if isinstance(message, str):
            return True, message

        recipient = None
        agent_input = None
        if "function_call" in message:
            name = message["function_call"].name
            agent_input = message["function_call"].arguments
            for ag in self.agents:
                if ag.name == name:
                    recipient = ag
                    break
        else:
            return True, message.get("content", "Nothing returned by LLM")

        if recipient is None:
            return True, f"{self.name} is not available now, please try again."

        # print(colored(f"Request for {recipient.name}:{agent_input}", "cyan"), flush=True)
        self.send(agent_input, recipient, request_reply=False)
        reply = recipient.generate_reply(sender=self)
        # print(colored(f"Response from {recipient.name}:{reply}", "cyan"), flush=True)
        # The recipient sends the message without requesting a reply
        recipient.send(reply, self, request_reply=False, silent=True)
        message = self.last_message(recipient)
        if "function_call" in message:
            final, response = recipient.generate_function_call_reply([message], recipient, config)
            if final:
                return True, response

        return True, message

    async def a_dispatching(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ):
        """
        Dispatches messages to the appropriate agents asynchronously.
        If there is no agent that can handle the message, fallback to manual mode.
        """
        final, response = self.generate_oai_reply(messages, sender, config)
        if not final:
            return True, f"{self.name} is not available now, please try again."

        message = self._message_to_dict(response)
        if isinstance(message, str):
            return True, message

        recipient = None
        agent_input = None
        if "function_call" in message:
            name = message["function_call"]["name"]
            agent_input = message["function_call"]["arguments"]
            for ag in self.agents:
                if ag.name == name:
                    recipient = ag
                    break
        else:
            return True, message.get("content", "Nothing returned by LLM")

        if recipient is None:
            return True, f"{self.name} is not available now, please try again."

        # print(colored(f"Request for {recipient.name}:{agent_input}", "cyan"), flush=True)
        self.send(agent_input, recipient, request_reply=False, silent=True)
        reply = recipient.generate_reply(sender=self)
        # print(colored(f"Response from {recipient.name}:{reply}", "cyan"), flush=True)
        # The recipient sends the message without requesting a reply
        recipient.a_send(reply, self, request_reply=False)
        message = self.last_message(recipient)
        if "function_call" in message:
            final, response = recipient.generate_function_call_reply([message], recipient, config)
            if final:
                return True, response

        return True, message
