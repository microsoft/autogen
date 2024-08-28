import datetime
import threading

from termcolor import colored

import autogencap.Config as Config

# Define log levels as constants
DEBUG = 0
INFO = 1
WARN = 2
ERROR = 3

# Map log levels to their names
LEVEL_NAMES = ["DBG", "INF", "WRN", "ERR"]
LEVEL_COLOR = ["dark_grey", "green", "yellow", "red"]


class BaseLogger:
    def __init__(self):
        self._lock = threading.Lock()

    def Log(self, level, context, msg):
        # Check if the current level meets the threshold
        if level >= Config.LOG_LEVEL:  # Use the LOG_LEVEL from the Config module
            # Check if the context is in the list of ignored contexts
            if context in Config.IGNORED_LOG_CONTEXTS:
                return
            with self._lock:
                self.WriteLog(level, context, msg)

    def WriteLog(self, level, context, msg):
        raise NotImplementedError("Subclasses must implement this method")


class ConsoleLogger(BaseLogger):
    def __init__(self, use_color=True):
        super().__init__()
        self._use_color = use_color

    def _colorize(self, msg, color):
        if self._use_color:
            return colored(msg, color)
        return msg

    def WriteLog(self, level, context, msg):
        timestamp = self._colorize(datetime.datetime.now().strftime("%m/%d/%y %H:%M:%S"), "dark_grey")
        # Translate level number to name and color
        level_name = self._colorize(LEVEL_NAMES[level], LEVEL_COLOR[level])
        # Left justify the context and color it blue
        context = self._colorize(context.ljust(14), "blue")
        # Left justify the threadid and color it blue
        thread_id = self._colorize(str(threading.get_ident()).ljust(5), "blue")
        # color the msg based on the level
        msg = self._colorize(msg, LEVEL_COLOR[level])
        print(f"{thread_id} {timestamp} {level_name}: [{context}] {msg}")


LOGGER = ConsoleLogger()


def Debug(context, message):
    LOGGER.Log(DEBUG, context, message)


def Info(context, message):
    LOGGER.Log(INFO, context, message)


def Warn(context, message):
    LOGGER.Log(WARN, context, message)


def Error(context, message):
    LOGGER.Log(ERROR, context, message)


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
