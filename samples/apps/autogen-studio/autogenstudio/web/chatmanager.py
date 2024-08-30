import asyncio
import os
import traceback
from datetime import datetime
from queue import Queue
from typing import Any, Dict, List, Optional
from loguru import logger

from ..datamodel import Message
from ..workflowmanager import WorkflowManager
from .websocketmanager import WebSocketConnectionManager


class AutoGenChatManager:
    """
    This class handles the automated generation and management of chat interactions
    using an automated workflow configuration and message queue.
    """

    def __init__(self, message_queue: Queue = None, websocket_manager: WebSocketConnectionManager = None) -> None:
        """
        Initializes the AutoGenChatManager with a message queue.

        :param message_queue: A queue to use for sending messages asynchronously.
        """
        self.message_queue = message_queue
        self.websocket_manager = websocket_manager

    def send(self, message: dict) -> None:
        """
        Sends a message by putting it into the message queue.

        :param message: The message string to be sent.
        """
        # Since we are no longer blocking the event loop in the main app.py,
        # we can safely avoid using the other thread, which increases complexity and
        # reduces certainty about the order in which messages will be sent.
        # if self.message_queue is not None:
        #     self.message_queue.put_nowait(message)
        for connection, socket_client_id in self.websocket_manager.active_connections:
            if message["connection_id"] == socket_client_id:
                logger.info(
                    f"Sending message to connection_id: {message['connection_id']}. Connection ID: {socket_client_id}, Message: {message}"
                )
                asyncio.run(self.websocket_manager.send_message(message, connection))
            else:
                logger.info(
                    f"Skipping message for connection_id: {message['connection_id']}. Connection ID: {socket_client_id}"
                )


    def get_user_input(self, user_prompt: dict, timeout: int) -> str:
        """
        waits on the websocket for a response from the user.

        :param prompt: the string to prompt the user with
        :param timeout: The amount of seconds to wait before considering the user inactive.
        :returns the user's response, or a default message to terminate the chat if the user is inactive.
        """
        response = ""
        for connection, socket_client_id in self.websocket_manager.active_connections:
            if user_prompt["connection_id"] == socket_client_id:
                logger.info(
                    f"Sending user prompt to connection_id: {user_prompt['connection_id']}. Connection ID: {socket_client_id}, Prompt: {user_prompt}"
                )
                response = asyncio.run(self.websocket_manager.get_user_input(user_prompt, timeout, connection))
            else:
                logger.info(
                    f"Skipping message for connection_id: {user_prompt['connection_id']}. Connection ID: {socket_client_id}"
                )

        return response


    def chat(
        self,
        message: Message,
        history: List[Dict[str, Any]],
        workflow: Any = None,
        connection_id: Optional[str] = None,
        user_dir: Optional[str] = None,
        human_input_function: Optional[callable] = None,
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
        :param user_dir: An optional base path to use as the temporary working folder.
        :param human_input_function: an optional callable to enable human input during workflows.
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
            human_input_function=human_input_function,
            connection_id=connection_id,
        )

        message_text = message.content.strip()
        # Temporary, for troubleshooting
        try:
            result_message: Message = workflow_manager.run(
                message=f"{message_text}", clear_history=False, history=history
            )
        except Exception:
            traceback.print_exc()
            raise

        result_message.user_id = message.user_id
        result_message.session_id = message.session_id
        return result_message
