import os
from datetime import datetime
from queue import Queue
from typing import Any, Dict, List, Optional, Tuple, Union

from loguru import logger

from .datamodel import Message
from .websocket_connection_manager import WebSocketConnectionManager
from .workflowmanager import WorkflowManager


class AutoGenChatManager:
    """
    This class handles the automated generation and management of chat interactions
    using an automated workflow configuration and message queue.
    """

    def __init__(
        self, message_queue: Queue, websocket_manager: WebSocketConnectionManager = None, human_input_timeout: int = 180
    ) -> None:
        """
        Initializes the AutoGenChatManager with a message queue.

        :param message_queue: A queue to use for sending messages asynchronously.
        """
        self.message_queue = message_queue
        self.websocket_manager = websocket_manager
        self.a_human_input_timeout = human_input_timeout

    def send(self, message: dict) -> None:
        """
        Sends a message by putting it into the message queue.

        :param message: The message string to be sent.
        """
        if self.message_queue is not None:
            self.message_queue.put_nowait(message)

    async def a_send(self, message: dict) -> None:
        """
        Asynchronously sends a message via the WebSocketManager class

        :param message: The message string to be sent.
        """
        for connection, socket_client_id in self.websocket_manager.active_connections:
            if message["connection_id"] == socket_client_id:
                logger.info(
                    f"Sending message to connection_id: {message['connection_id']}. Connection ID: {socket_client_id}"
                )
                await self.websocket_manager.send_message(message, connection)
            else:
                logger.info(
                    f"Skipping message for connection_id: {message['connection_id']}. Connection ID: {socket_client_id}"
                )

    async def a_prompt_for_input(self, prompt: dict, timeout: int = 60) -> str:
        """
        Sends the user a prompt and waits for a response asynchronously via the WebSocketManager class

        :param message: The message string to be sent.
        """

        for connection, socket_client_id in self.websocket_manager.active_connections:
            if prompt["connection_id"] == socket_client_id:
                logger.info(
                    f"Sending message to connection_id: {prompt['connection_id']}. Connection ID: {socket_client_id}"
                )
                try:
                    result = await self.websocket_manager.get_input(prompt, connection, timeout)
                    return result
                except Exception as e:
                    return f"Error: {e}\nTERMINATE"
            else:
                logger.info(
                    f"Skipping message for connection_id: {prompt['connection_id']}. Connection ID: {socket_client_id}"
                )

    def chat(
        self,
        message: Message,
        history: List[Dict[str, Any]],
        workflow: Any = None,
        connection_id: Optional[str] = None,
        user_dir: Optional[str] = None,
        **kwargs,
    ) -> Message:
        """
        Processes an incoming message according to the agent's workflow configuration
        and generates a response.

        :param message: An instance of `Message` representing an incoming message.
        :param history: A list of dictionaries, each representing a past interaction.
        :param flow_config: An instance of `AgentWorkFlowConfig`. If None, defaults to a standard configuration.
        :param connection_id: An optional connection identifier.
        :param kwargs: Additional keyword arguments.
        :return: An instance of `Message` representing a response.
        """

        # create a working director for workflow based on user_dir/session_id/time_hash
        work_dir = os.path.join(
            user_dir,
            str(message.session_id),
            datetime.now().strftime("%Y%m%d_%H-%M-%S"),
        )
        os.makedirs(work_dir, exist_ok=True)

        # if no flow config is provided, use the default
        if workflow is None:
            raise ValueError("Workflow must be specified")

        workflow_manager = WorkflowManager(
            workflow=workflow,
            history=history,
            work_dir=work_dir,
            send_message_function=self.send,
            a_send_message_function=self.a_send,
            connection_id=connection_id,
        )

        message_text = message.content.strip()
        result_message: Message = workflow_manager.run(message=f"{message_text}", clear_history=False, history=history)

        result_message.user_id = message.user_id
        result_message.session_id = message.session_id
        return result_message

    async def a_chat(
        self,
        message: Message,
        history: List[Dict[str, Any]],
        workflow: Any = None,
        connection_id: Optional[str] = None,
        user_dir: Optional[str] = None,
        **kwargs,
    ) -> Message:
        """
        Processes an incoming message according to the agent's workflow configuration
        and generates a response.

        :param message: An instance of `Message` representing an incoming message.
        :param history: A list of dictionaries, each representing a past interaction.
        :param flow_config: An instance of `AgentWorkFlowConfig`. If None, defaults to a standard configuration.
        :param connection_id: An optional connection identifier.
        :param kwargs: Additional keyword arguments.
        :return: An instance of `Message` representing a response.
        """

        # create a working director for workflow based on user_dir/session_id/time_hash
        work_dir = os.path.join(
            user_dir,
            str(message.session_id),
            datetime.now().strftime("%Y%m%d_%H-%M-%S"),
        )
        os.makedirs(work_dir, exist_ok=True)

        # if no flow config is provided, use the default
        if workflow is None:
            raise ValueError("Workflow must be specified")

        workflow_manager = WorkflowManager(
            workflow=workflow,
            history=history,
            work_dir=work_dir,
            send_message_function=self.send,
            a_send_message_function=self.a_send,
            a_human_input_function=self.a_prompt_for_input,
            a_human_input_timeout=self.a_human_input_timeout,
            connection_id=connection_id,
        )

        message_text = message.content.strip()
        result_message: Message = await workflow_manager.a_run(
            message=f"{message_text}", clear_history=False, history=history
        )

        result_message.user_id = message.user_id
        result_message.session_id = message.session_id
        return result_message
