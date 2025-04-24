from autogen_core import (
    MessageContext,
    RoutedAgent,
    message_handler,
)

from autogen_core.model_context import BufferedChatCompletionContext

from models import AgentResponse
import asyncio
import json
import os



class UserAgent(RoutedAgent):
    def __init__(self, 
                 description: str, 
                 user_topic_type: str, 
                 agent_topic_type: str, 
                 response_queue : asyncio.Queue[str | object], 
                 stream_done : object) -> None:
        super().__init__(description)
        self._user_topic_type = user_topic_type
        self._agent_topic_type = agent_topic_type
        self._response_queue = response_queue
        self._STREAM_DONE = stream_done

    @message_handler
    async def handle_task_result(self, message: AgentResponse, ctx: MessageContext) -> None:
        #Save chat history
        context = BufferedChatCompletionContext(buffer_size=10,initial_messages=message.context)
        save_context = await context.save_state()
        # Save context to JSON file
        chat_history_dir = "chat_history"
        if ctx.topic_id is None:
            raise ValueError("MessageContext.topic_id is None, cannot save chat history")
        file_path = os.path.join(chat_history_dir, f"{ctx.topic_id.source}.json")
        with open(file_path, 'w') as f:
            json.dump(save_context, f, indent=4)
        
        #End stream
        await self._response_queue.put(self._STREAM_DONE)

