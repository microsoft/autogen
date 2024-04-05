#!/usr/bin/env python

import asyncio
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Iterator

import uvicorn  # noqa: E402
from websockets.sync.client import connect as ws_connect

import autogen
from autogen.io.websockets import IOWebsockets

file_location = Path(__file__).parents[3] / "notebook"
assert file_location.exists(), file_location

config_list = autogen.config_list_from_json(
    "OAI_CONFIG_LIST",
    file_location=file_location,
    filter_dict={
        "model": ["gpt-4", "gpt-3.5-turbo", "gpt-3.5-turbo-16k"],
    },
)

assert config_list[0]["model"] is not None


def on_connect(iostream: IOWebsockets) -> None:
    print(f" - on_connect(): Connected to client using IOWebsockets {iostream}", flush=True)

    print(" - on_connect(): Receiving message from client.", flush=True)

    initial_msg = iostream.input()

    llm_config = {
        "config_list": config_list,
        "stream": True,
    }

    agent = autogen.ConversableAgent(
        name="chatbot",
        system_message="Complete a task given to you and reply TERMINATE when the task is done. If asked about the weather, use tool weather_forecast(city) to get the weather forecast for a city.",
        llm_config=llm_config,
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

    @user_proxy.register_for_execution()
    @agent.register_for_llm(description="Weather forecats for a city")
    def weather_forecast(city: str) -> str:
        return f"The weather forecast for {city} at {datetime.now()} is sunny."

    # we will use a temporary directory as the cache path root to ensure fresh completion each time
    print(
        f" - on_connect(): Initiating chat with agent {agent} using message '{initial_msg}'",
        flush=True,
    )
    user_proxy.initiate_chat(  # noqa: F704
        agent,
        message=initial_msg,
    )


from contextlib import asynccontextmanager  # noqa: E402
from pathlib import Path  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import HTMLResponse  # noqa: E402

PORT = 8000

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
        print(f"Websocket server started at {uri}.", flush=True)

        yield


app = FastAPI(lifespan=run_websocket_server)


@app.get("/")
async def get() -> HTMLResponse:
    return HTMLResponse(html)


async def start_uvicorn() -> None:
    config = uvicorn.Config(app)
    server = uvicorn.Server(config)
    await server.serve()  # noqa: F704


if __name__ == "__main__":
    asyncio.run(start_uvicorn())
