# tinyra.py

import argparse
from typing import Dict, Optional

from autogen import config_list_from_json
from autogen import AssistantAgent
from autogen import UserProxyAgent
from autogen.agentchat.contrib.teachable_agent import TeachableAgent

CONFIG_FILE = "./OAI_CONFIG_LIST"
WORK_DIR = "./coding"


def run(config_file: Optional[str] = CONFIG_FILE, work_dir: Optional[str] = WORK_DIR):
    config_list = config_list_from_json(config_file)

    coder = TeachableAgent(
        "assistant",
        system_message=AssistantAgent.DEFAULT_SYSTEM_MESSAGE,
        llm_config={"config_list": config_list},
        teach_config={"verbosity": 1, "auto_learn": True},
    )
    user_proxy = UserProxyAgent(
        "user_proxy",
        code_execution_config={"work_dir": work_dir},
        human_input_mode="TERMINATE",
        is_termination_msg=lambda x: "TERMINATE" in x.get("content"),
    )

    coder.initiate_chat(user_proxy, message="Welcome! How can I help? TERMINATE")


def main():
    parser = argparse.ArgumentParser(description="TinyRA: A minimalistic Research Assistant.")
    parser.add_argument("-c", default=CONFIG_FILE, help="Path to the config file")
    parser.add_argument("-w", default=WORK_DIR, help="Path to the working directory")
    args = parser.parse_args()

    run(config_file=args.c, work_dir=args.w)


if __name__ == "__main__":
    main()
