import asyncio
import os
from datetime import datetime
from queue import Queue
from typing import Any, Dict, List, Optional, Tuple, Union

import websockets
from fastapi import WebSocket, WebSocketDisconnect

from .datamodel import Message
from .workflowmanager import WorkflowManager


class AutoGenChatManager:
    """
    This class handles the automated generation and management of chat interactions
    using an automated workflow configuration and message queue.
    """

    def __init__(self, message_queue: Queue) -> None:
        """
        Initializes the AutoGenChatManager with a message queue.

        :param message_queue: A queue to use for sending messages asynchronously.
        """
        self.message_queue = message_queue

    def send(self, message: str) -> None:
        """
        Sends a message by putting it into the message queue.

        :param message: The message string to be sent.
        """
        if self.message_queue is not None:
            self.message_queue.put_nowait(message)

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
            connection_id=connection_id,
        )

        message_text = message.content.strip()
        result_message: Message = workflow_manager.run(message=f"{message_text}", clear_history=False, history=history)

        result_message.user_id = message.user_id
        result_message.session_id = message.session_id
        return result_message
