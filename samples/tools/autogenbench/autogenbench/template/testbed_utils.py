import json
import os
from datetime import datetime

from pkg_resources import packaging

import autogen

AUTOGEN_VERSION = packaging.version.parse(autogen.__version__)

# Try importing the runtime_logging module (only available in some branches)
LOGGING_ENABLED = False
try:
    import autogen.runtime_logging

    LOGGING_ENABLED = True
except ImportError:
    pass


def default_llm_config(config_list, timeout=180):
    """Return a default config list with a given timeout, and with caching disabled.
    The formatting depends on the version of Autogen installed.

    Args:
        config_list (list): the OAI config list to include in the final llm_config
        timeout (int): the timeout for calls to the LLM

    Returns:
        None
    """
    llm_config = {
        "config_list": config_list,
    }

    # Add options depending on the version
    if AUTOGEN_VERSION < packaging.version.parse("0.2.0b1"):
        llm_config["request_timeout"] = timeout
        llm_config["use_cache"] = False
    elif AUTOGEN_VERSION < packaging.version.parse("0.2.0b4"):
        llm_config["timeout"] = timeout
        llm_config["cache"] = None
    else:
        llm_config["timeout"] = timeout
        llm_config["cache_seed"] = None

    return llm_config


def init():
    """Helper function to initialize logging in a testbed scenario.
    Specifically, write timestamp and version information, then
    initialize autogen logging.

    Args:
        None

    Returns:
        None
    """

    # Print some information about the run
    with open("timestamp.txt", "wt") as f:
        f.write("Timestamp: " + datetime.now().isoformat() + "\n")
        f.write("autogen-agentchat version: " + str(autogen.__version__) + "\n")

    # Start logging
    if AUTOGEN_VERSION < packaging.version.parse("0.2.0b1"):
        autogen.Completion.start_logging(compact=False)

    # Start logging
    if LOGGING_ENABLED:
        autogen.runtime_logging.start(config={"dbname": "telemetry.sqlite"})


def finalize(agents):
    """Helper function to finalize logging in a testbed scenario.
    Calling this function will save all the chat completions logged
    by Autogen to disk, and will save the messages dictionaries of
    all agents passed via the agents argument.

    Args:
        agents (list): a list of the agents whose messages will be logged to disk.

    Returns:
        None
    """

    script_dir = os.path.dirname(os.path.realpath(__file__))

    def messages_to_json(agent):
        messages = dict()
        for item in agent.chat_messages.items():
            messages[item[0].name] = item[1]
        return json.dumps(messages, indent=4)

    for agent in agents:
        fname = agent.name + "_messages.json"
        with open(os.path.join(script_dir, fname), "wt") as fh:
            fh.write(messages_to_json(agent))

    # Stop logging, and write logs to disk
    if AUTOGEN_VERSION < packaging.version.parse("0.2.0b1"):
        with open(os.path.join(script_dir, "completion_log.json"), "wt") as fh:
            fh.write(json.dumps(autogen.Completion.logged_history, indent=4))
        autogen.Completion.stop_logging()

    # Stop logging
    if LOGGING_ENABLED:
        autogen.runtime_logging.stop()
