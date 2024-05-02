from typing import List, Optional
import re

from .message import Message


def parse_agb_console(file_path: str) -> List[Message]:

    # read the lines in file one by one
    with open(file_path, "r") as file:
        lines = file.readlines()

    in_start = False
    in_main_task = False

    all_lines = []
    main_lines = []

    for line in lines:

        if "SCENARIO.PY STARTING !#!#" in line:
            in_start = True
            continue

        if "SCENARIO.PY COMPLETE !#!#" in line:
            in_start = False
            continue

        if "MAIN TASK STARTING !#!#" in line:
            in_main_task = True
            continue

        if "MAIN TASK COMPLETE !#!#" in line:
            in_main_task = False
            continue

        if in_start:
            all_lines.append(line)

        if in_main_task:
            main_lines.append(line)

    all_console_lines = "".join(all_lines)

    if len(all_console_lines) == 0:
        raise Exception(
            "No console output found. Please ensure the log contains the string 'SCENARIO.PY STARTING !#!#' and 'SCENARIO.PY COMPLETE !#!#'"
        )

    main_lines = "".join(main_lines)

    all_messages_str = all_console_lines.split(
        "--------------------------------------------------------------------------------"
    )
    main_messages_str = main_lines.split(
        "--------------------------------------------------------------------------------"
    )

    if len(all_messages_str) == 0:
        raise Exception("No messages found in console log")

    messages = []

    def parse_source(line: str) -> Optional[str]:
        """Parse the source from a line. Return None if no source is found."""
        regex = re.compile(r"(\w+) \(to (\w+)\):")
        matches = regex.search(line)
        if matches:
            return matches.group(1)  # return the source
        else:
            return None

    # ignore the last message from the logs as it is evaluation
    all_messages_str = all_messages_str[:-1]

    first_main_msg_idx = None
    last_main_msg_idx = None

    for i, msg_str in enumerate(all_messages_str):

        source = None

        for line in msg_str.split("\n"):
            source = parse_source(line)
            if source is not None:
                break

        if source is None:
            raise Exception(
                f"Could not find source for message: {msg_str}. Please ensure all messages have a source in the format `source (to target)`."
            )

        if not first_main_msg_idx and msg_str in main_messages_str:
            first_main_msg_idx = i
            last_main_msg_idx = i + len(main_messages_str)

        if first_main_msg_idx and last_main_msg_idx:
            if i in range(first_main_msg_idx, last_main_msg_idx):
                in_main_task = True
            else:
                in_main_task = False

        msg = Message(
            source=source, role=source, content=msg_str, tags=["in_main_task"] if in_main_task else None
        )  # add tag if message is in main task
        messages.append(msg)
    return messages
