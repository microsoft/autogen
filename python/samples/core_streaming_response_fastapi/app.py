from fastapi import FastAPI, HTTPException, Header, Depends,Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel,Field
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

import os
import json
import time

import asyncio


from autogen_core import (
    AgentId,
    ClosureAgent,
    ClosureContext,
    DefaultTopicId,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    TopicId,
    TypeSubscription,
    default_subscription,
    message_handler,
    type_subscription,
)

from autogen_core.models import ChatCompletionClient, SystemMessage, UserMessage,AssistantMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient

app = FastAPI()


@dataclass
class LlmResponse:
    """
    Represents the final accumulated response content from the LLM agent.
    Note: The 'content' field currently holds the full string, not individual chunks.
    """
    content: list

@dataclass
class ChatHistory:
    """
    Represents the chat history, containing a list of messages.
    Each message is expected to be a dictionary with 'source' and 'content' keys.
    """
    messages: List[Dict[str, str]]

# Queue for streaming results from the agent back to the request handler
response_queue = asyncio.Queue()
# Sentinel object to signal the end of the stream
STREAM_DONE = object()


    
async def main(msg:list):
    """
    Sends messages to the agent and yields results received via the queue.

    Args:
        msg (list): A list of message dictionaries conforming to ChatHistory.

    Yields:
        str: JSON strings representing message chunks or completion signals.
    """
    message = ChatHistory(messages=msg)
    task1 = asyncio.create_task(runtime.send_message(message, AgentId("simple_agent", "default")))
    
    # Consume items from the response queue until the stream ends or an error occurs
    while True:
        item = await response_queue.get()
        if item is STREAM_DONE:
            print(f"{time.time():.2f} - MAIN: Received STREAM_DONE. Exiting loop.")
            break
        elif isinstance(item, str) and item.startswith("ERROR:"):
            print(f"{time.time():.2f} - MAIN: Received error message from agent: {item}")
            break
        else:
            yield json.dumps({'content': item}) + '\n'
    await task1           
    return
    

@type_subscription(topic_type="simple_agent")
class MyAgent(RoutedAgent):
    def __init__(self,name:str, model_client: ChatCompletionClient) -> None:
        super().__init__(name)
        self._system_messages = [SystemMessage(content="You are a helpful assistant.")]
        self._model_client = model_client
        self._response_queue = response_queue

    @message_handler
    async def handle_user_message(self, message: ChatHistory, ctx: MessageContext) -> LlmResponse:
        accumulated_content = '' # To store the full response.
        try:
            _message = message.messages
            user_message = [UserMessage(**i) if i['source']=='user' else AssistantMessage(**i) for i in  _message ]
            async for i in self._model_client.create_stream(
                user_message, cancellation_token=ctx.cancellation_token
            ):
                if isinstance(i,str):
                    accumulated_content+=i
                    await self._response_queue.put(i)
                else:
                    break
            await self._response_queue.put(STREAM_DONE)
            return LlmResponse(content=accumulated_content)
        except Exception as e:
            await self._response_queue.put('ERROR:'+e)
            return LlmResponse(content=e)

runtime = SingleThreadedAgentRuntime()


@app.post("/chat/completions")
async def chat_completions_stream(request:Request):
    json_data = await request.json()
    messages = json_data.get('messages','')
    if isinstance(messages,list):
        return StreamingResponse(main(messages),media_type="text/plain")
    else:
        raise HTTPException(status_code=400, detail="Invalid input: 'messages' must be a list.")


@app.on_event("startup")
async def startup_event():
    await MyAgent.register(
        runtime,
        "simple_agent",
        lambda: MyAgent('myagent',
            OpenAIChatCompletionClient(
                model="gemini-2.0-flash",
                api_key="YOUR_API_KEY_HERE",
            )
        ),
    )
    runtime.start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8501)
