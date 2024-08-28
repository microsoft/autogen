import time
from typing import Callable, Dict, List, Optional, Union

from autogen import Agent, ConversableAgent

from ..actor_runtime import IRuntime
from .AutoGenConnector import AutoGenConnector


class AG2CAP(ConversableAgent):
    """
    A conversable agent proxy that sends messages to CAN when called
    """

    def __init__(
        self,
        ensemble: IRuntime,
        agent_name: str,
        agent_description: Optional[str] = None,
    ):
        super().__init__(name=agent_name, description=agent_description, llm_config=False)
        self._agent_connector: AutoGenConnector = None
        self._ensemble: IRuntime = ensemble
        self._recv_called = False

    def reset_receive_called(self):
        self._recv_called = False

    def was_receive_called(self):
        return self._recv_called

    def set_name(self, name: str):
        """
        Set the name of the agent.
        Why? because we need it to look like different agents
        """
        self._name = name

    def _check_connection(self):
        if self._agent_connector is None:
            self._agent_connector = AutoGenConnector(self._ensemble.find_by_name(self.name))
            self._terminate_connector = AutoGenConnector(self._ensemble.find_termination())

    def receive(
        self,
        message: Union[Dict, str],
        sender: Agent,
        request_reply: Optional[bool] = None,
        silent: Optional[bool] = False,
    ):
        """
        Receive a message from the AutoGen system.
        """
        self._recv_called = True
        self._check_connection()
        self._agent_connector.send_receive_req(message, sender, request_reply, silent)

    def generate_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        exclude: Optional[List[Callable]] = None,
    ) -> Union[str, Dict, None]:
        """
        Generate a reply message for the AutoGen system.
        """
        self._check_connection()
        return self._agent_connector.send_gen_reply_req()

    def _prepare_chat(
        self,
        recipient: ConversableAgent,
        clear_history: bool,
        prepare_recipient: bool = True,
        reply_at_receive: bool = True,
    ) -> None:
        self._check_connection()
        self._agent_connector.send_prep_chat(recipient, clear_history, prepare_recipient)

    def send_terminate(self, recipient: ConversableAgent) -> None:
        self._check_connection()
        self._agent_connector.send_terminate(recipient)
        self._terminate_connector.send_terminate(self)
