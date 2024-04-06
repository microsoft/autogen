#!/usr/bin/env python

import asyncio
import logging
import os
from contextlib import asynccontextmanager  # noqa: E402
from datetime import datetime
from typing import AsyncIterator, Dict, Iterator, List

import uvicorn  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.responses import HTMLResponse  # noqa: E402
from websockets.sync.client import connect as ws_connect

import autogen
from autogen.io.websockets import IOWebsockets

PORT = 8000

# logger = getLogger(__name__)
logger = logging.getLogger("uvicorn")


def _get_config_list() -> List[Dict[str, str]]:
    """Get a list of config dictionaries with API keys for OpenAI and Azure OpenAI.

    Returns:
        List[Dict[str, str]]: A list of config dictionaries with API keys.

    Example:
        >>> _get_config_list()
        [
            {
                'model': 'gpt-35-turbo-16k',
                'api_key': '0123456789abcdef0123456789abcdef',
                'base_url': 'https://my-deployment.openai.azure.com/',
                'api_type': 'azure',
                'api_version': '2024-02-15-preview',
            },
            {
                'model': 'gpt-4',
                'api_key': '0123456789abcdef0123456789abcdef',
            },
        ]
    """
    # can use both OpenAI and Azure OpenAI API keys
    config_list = [
        {
            "model": "gpt-35-turbo-16k",
            "api_key": os.environ.get("AZURE_OPENAI_API_KEY"),
            "base_url": os.environ.get("AZURE_OPENAI_BASE_URL"),
            "api_type": "azure",
            "api_version": os.environ.get("AZURE_OPENAI_API_VERSION"),
        },
        {
            "model": "gpt-4",
            "api_key": os.environ.get("OPENAI_API_KEY"),
        },
    ]
    # filter out configs with no API key
    config_list = [llm_config for llm_config in config_list if llm_config["api_key"] is not None]

    if not config_list:
        raise ValueError(
            "No API keys found. Please set either AZURE_OPENAI_API_KEY or OPENAI_API_KEY environment variable."
        )

    return config_list


def on_connect(iostream: IOWebsockets) -> None:
    logger.info(f"on_connect(): Connected to client using IOWebsockets {iostream}")

    logger.info("on_connect(): Receiving message from client.")

    # get the initial message from the client
    initial_msg = iostream.input()

    # instantiate an agent named "chatbot"
    agent = autogen.ConversableAgent(
        name="chatbot",
        system_message="Complete a task given to you and reply TERMINATE when the task is done. If asked about the weather, use tool weather_forecast(city) to get the weather forecast for a city.",
        llm_config={
            "config_list": _get_config_list(),
            "stream": True,
        },
    )

    # create a UserProxyAgent instance named "user_proxy"
    user_proxy = autogen.UserProxyAgent(
        name="user_proxy",
        system_message="A proxy for the user.",
        is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
        human_input_mode="NEVER",
        max_consecutive_auto_reply=10,
        code_execution_config=False,
    )

    # register the weather_forecast function
    def weather_forecast(city: str) -> str:
        return f"The weather forecast for {city} at {datetime.now()} is sunny."

    autogen.register_function(
        weather_forecast, caller=agent, executor=user_proxy, description="Weather forecast for a city"
    )

    # instantiate a chat
    logger.info(
        f"on_connect(): Initiating chat with the agent ({agent.name}) and the user proxy ({user_proxy.name}) using the message '{initial_msg}'",
    )
    user_proxy.initiate_chat(  # noqa: F704
        agent,
        message=initial_msg,
    )

    logger.info("on_connect(): Finished the task successfully.")


html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Autogen websocket test</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off" value="Write a poem about the current wearther in Paris or London, you choose."/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://localhost:8080/ws");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


@asynccontextmanager
async def run_websocket_server(app: FastAPI) -> AsyncIterator[None]:
    with IOWebsockets.run_server_in_thread(on_connect=on_connect, port=8080) as uri:
        logger.info(f"Websocket server started at {uri}.")

        yield


app = FastAPI(lifespan=run_websocket_server)


@app.get("/")
async def get() -> HTMLResponse:
    return HTMLResponse(html)


async def start_uvicorn() -> None:
    config = uvicorn.Config(app)
    server = uvicorn.Server(config)
    try:
        await server.serve()  # noqa: F704
    except KeyboardInterrupt:
        logger.info("Shutting down server")


if __name__ == "__main__":
    # set the log level to INFO
    logger.setLevel("INFO")
    asyncio.run(start_uvicorn())
