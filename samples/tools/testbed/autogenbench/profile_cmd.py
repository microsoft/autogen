import os
import json
import sys
import argparse
import errno
from autogen import config_list_from_json
from .profiler import annotate_chat_history

# Figure out where everything is
SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_NAME = os.path.basename(SCRIPT_PATH)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)


def run_profiler(logs_path, config_list):
    chat_history = dict()
    with open(logs_path, "rt") as fh:
        chat_history = json.loads(fh.read())
        chat_history = next(iter(chat_history.values()))

    llm_config = {
        "config_list": config_list,
    }

    labels = annotate_chat_history(chat_history, llm_config=llm_config)
    print(json.dumps(labels, indent=4))


def profile_cli(invocation_cmd="autogenbench profile", cli_args=None):
    # Prepare the argument parser
    parser = argparse.ArgumentParser(
        prog=invocation_cmd,
        description=f"{invocation_cmd} will run the AutoGen agent profiler the logs produced from a prior run.",
    )

    parser.add_argument(
        "runlogs",
        nargs="?",
        help="the path to where the run logs are stored.",
    )

    parser.add_argument(
        "-c",
        "--config",
        type=str,
        help="The environment variable name or path to the OAI_CONFIG_LIST (default: OAI_CONFIG_LIST).",
        default="OAI_CONFIG_LIST",
    )

    # In most cases just parse args from sys.arv[1:], which is the parse_args default
    args = None
    if cli_args is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(cli_args)

    if not args.runlogs:
        parser.error("the following arguments are required: runlogs")

    # Load the OAI_CONFIG_LIST
    config_list = config_list_from_json(env_or_file=args.config)
    if len(config_list) == 0:
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), args.config)

    run_profiler(args.runlogs, config_list)
