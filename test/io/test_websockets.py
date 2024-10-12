from tempfile import TemporaryDirectory
from typing import Dict

import pytest
from conftest import skip_openai

import autogen
from autogen.cache.cache import Cache
from autogen.io import IOWebsockets
from autogen.io.base import IOStream

KEY_LOC = "notebook"
OAI_CONFIG_LIST = "OAI_CONFIG_LIST"

# Check if the websockets module is available
try:
    from websockets.sync.client import connect as ws_connect
except ImportError:  # pragma: no cover
    skip_test = True
else:
    skip_test = False


@pytest.mark.skipif(skip_test, reason="websockets module is not available")
class TestConsoleIOWithWebsockets:
    def test_input_print(self) -> None:
        print()
        print("Testing input/print", flush=True)

        def on_connect(iostream: IOWebsockets) -> None:
            print(f" - on_connect(): Connected to client using IOWebsockets {iostream}", flush=True)

            print(" - on_connect(): Receiving message from client.", flush=True)

            msg = iostream.input()

            print(f" - on_connect(): Received message '{msg}' from client.", flush=True)

            assert msg == "Hello world!"

            for msg in ["Hello, World!", "Over and out!"]:
                print(f" - on_connect(): Sending message '{msg}' to client.", flush=True)

                iostream.print(msg)

            print(" - on_connect(): Receiving message from client.", flush=True)

            msg = iostream.input("May I?")

            print(f" - on_connect(): Received message '{msg}' from client.", flush=True)
            assert msg == "Yes"

            return

        with IOWebsockets.run_server_in_thread(on_connect=on_connect, port=8765) as uri:
            print(f" - test_setup() with websocket server running on {uri}.", flush=True)

            with ws_connect(uri) as websocket:
                print(f" - Connected to server on {uri}", flush=True)

                print(" - Sending message to server.", flush=True)
                websocket.send("Hello world!")

                for expected in ["Hello, World!", "Over and out!", "May I?"]:
                    print(" - Receiving message from server.", flush=True)
                    message = websocket.recv()
                    message = message.decode("utf-8") if isinstance(message, bytes) else message
                    # drop the newline character
                    if message.endswith("\n"):
                        message = message[:-1]

                    print(
                        f"   - Asserting received message '{message}' is the same as the expected message '{expected}'",
                        flush=True,
                    )
                    assert message == expected

                print(" - Sending message 'Yes' to server.", flush=True)
                websocket.send("Yes")

        print("Test passed.", flush=True)

    @pytest.mark.skipif(skip_openai, reason="requested to skip")
    def test_chat(self) -> None:
        print("Testing setup", flush=True)

        success_dict = {"success": False}

        def on_connect(iostream: IOWebsockets, success_dict: Dict[str, bool] = success_dict) -> None:
            print(f" - on_connect(): Connected to client using IOWebsockets {iostream}", flush=True)

            print(" - on_connect(): Receiving message from client.", flush=True)

            initial_msg = iostream.input()

            config_list = autogen.config_list_from_json(
                OAI_CONFIG_LIST,
                filter_dict={
                    "model": [
                        "gpt-4o-mini",
                        "gpt-3.5-turbo",
                    ],
                },
                file_location=KEY_LOC,
            )

            llm_config = {
                "config_list": config_list,
                "stream": True,
            }

            agent = autogen.ConversableAgent(
                name="chatbot",
                system_message="Complete a task given to you and reply TERMINATE when the task is done.",
                llm_config=llm_config,
            )

            # create a UserProxyAgent instance named "user_proxy"
            user_proxy = autogen.UserProxyAgent(
                name="user_proxy",
                system_message="A proxy for the user.",
                is_termination_msg=lambda x: x.get("content", "")
                and x.get("content", "").rstrip().endswith("TERMINATE"),
                human_input_mode="NEVER",
                max_consecutive_auto_reply=10,
            )

            # we will use a temporary directory as the cache path root to ensure fresh completion each time
            with TemporaryDirectory() as cache_path_root:
                with Cache.disk(cache_path_root=cache_path_root) as cache:
                    print(
                        f" - on_connect(): Initiating chat with agent {agent} using message '{initial_msg}'",
                        flush=True,
                    )
                    user_proxy.initiate_chat(  # noqa: F704
                        agent,
                        message=initial_msg,
                        cache=cache,
                    )

            success_dict["success"] = True

            return

        with IOWebsockets.run_server_in_thread(on_connect=on_connect, port=8765) as uri:
            print(f" - test_setup() with websocket server running on {uri}.", flush=True)

            with ws_connect(uri) as websocket:
                print(f" - Connected to server on {uri}", flush=True)

                print(" - Sending message to server.", flush=True)
                # websocket.send("2+2=?")
                websocket.send("Please write a poem about spring in a city of your choice.")

                while True:
                    message = websocket.recv()
                    message = message.decode("utf-8") if isinstance(message, bytes) else message
                    # drop the newline character
                    if message.endswith("\n"):
                        message = message[:-1]

                    print(message, end="", flush=True)

                    if "TERMINATE" in message:
                        print()
                        print(" - Received TERMINATE message. Exiting.", flush=True)
                        break

        assert success_dict["success"]
        print("Test passed.", flush=True)
