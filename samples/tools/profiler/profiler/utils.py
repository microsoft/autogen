from typing import List
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
    main_lines = "".join(main_lines)

    all_messages = all_console_lines.split(
        "--------------------------------------------------------------------------------"
    )

    messages = []

    for msg in all_messages:

        for line in msg.split("\n"):
            if "(to " in line and line.endswith(":"):
                source = line.split(" (")[0]

                messages.append(
                    Message(
                        source=source, role=source, content=msg, tags=["in_main_task"] if msg in main_lines else None
                    )  # add tag if message is in main task
                )

    return messages
