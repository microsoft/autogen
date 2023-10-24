from importlib.metadata import version as lib_version
from datetime import datetime
import os
import autogen
import json


def init():
    autogen.ChatCompletion.start_logging(compact=False)

    # Print some information about the run
    with open("timestamp.txt", "wt") as f:
        f.write("Timestamp: " + datetime.now().isoformat() + "\n")
        f.write("pyautogen version: " + lib_version("pyautogen") + "\n")


def finalize(*args):
    script_dir = os.path.dirname(os.path.realpath(__file__))

    with open(os.path.join(script_dir, "chat_completions.json"), "wt") as fh:
        fh.write(json.dumps(autogen.ChatCompletion.logged_history, indent=4))
        autogen.ChatCompletion.stop_logging()

    def messages_to_json(agent):
        messages = dict()
        for item in agent.chat_messages.items():
            messages[item[0].name] = item[1]
        return json.dumps(messages, indent=4)

    for arg in args:
        fname = arg.name + "_messages.json"
        with open(os.path.join(script_dir, fname), "wt") as fh:
            fh.write(messages_to_json(arg))
