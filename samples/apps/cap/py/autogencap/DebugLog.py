import threading
import datetime
from autogencap.Config import LOG_LEVEL, IGNORED_LOG_CONTEXTS
from termcolor import colored

# Define log levels as constants
DEBUG = 0
INFO = 1
WARN = 2
ERROR = 3

# Map log levels to their names
LEVEL_NAMES = ["DBG", "INF", "WRN", "ERR"]
LEVEL_COLOR = ["dark_grey", "green", "yellow", "red"]

console_lock = threading.Lock()


def Log(level, context, msg):
    # Check if the current level meets the threshold
    if level >= LOG_LEVEL:  # Use the LOG_LEVEL from the Config module
        # Check if the context is in the list of ignored contexts
        if context in IGNORED_LOG_CONTEXTS:
            return
        with console_lock:
            timestamp = colored(datetime.datetime.now().strftime("%m/%d/%y %H:%M:%S"), "dark_grey")
            # Translate level number to name and color
            level_name = colored(LEVEL_NAMES[level], LEVEL_COLOR[level])
            # Center justify the context and color it blue
            context = colored(context.ljust(14), "blue")
            # color the msg based on the level
            msg = colored(msg, LEVEL_COLOR[level])
            print(f"{threading.get_ident()} {timestamp} {level_name}: [{context}] {msg}")


def Debug(context, message):
    Log(DEBUG, context, message)


def Info(context, message):
    Log(INFO, context, message)


def Warn(context, message):
    Log(WARN, context, message)


def Error(context, message):
    Log(ERROR, context, message)


def shorten(msg, num_parts=5, max_len=100):
    # Remove new lines
    msg = msg.replace("\n", " ")

    # If the message is shorter than or equal to max_len characters, return it as is
    if len(msg) <= max_len:
        return msg

    # Calculate the length of each part
    part_len = max_len // num_parts

    # Create a list to store the parts
    parts = []

    # Get the parts from the message
    for i in range(num_parts):
        start = i * part_len
        end = start + part_len
        parts.append(msg[start:end])

    # Join the parts with '...' and return the result
    return "...".join(parts)
