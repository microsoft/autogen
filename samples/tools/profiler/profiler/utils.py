from typing import List
from .message import Message


def parse_agb_console(file_path: str) -> List[Message]:

    # read the lines in file one by one
    with open(file_path, "r") as file:
        lines = file.readlines()

    # extract the text between the lines that are SCENARIO.PY STARTING !#!# and SCENARIO.PY COMPLETE !#!#
    start = False
    chat_history_json = []
    for line in lines:
        if "SCENARIO.PY STARTING !#!#" in line:
            start = True
        elif "SCENARIO.PY COMPLETE !#!#" in line:
            start = False
        elif start:
            chat_history_json.append(line)

    main_console_log = "".join(chat_history_json)

    chat_history_json = main_console_log.split(
        "--------------------------------------------------------------------------------"
    )

    messages = []
    for msg in chat_history_json:
        for line in msg.split("\n"):
            if "(to " in line and line.endswith(":"):
                source = line.split(" (")[0]
                messages.append(Message(source=source, role=source, content=msg))

    return messages
