"""
Demo App
"""
import os
import sys

from demo.SimpleActorDemo import simple_actor_demo
from demo.AGDemo import ag_demo
from demo.AGGroupChatDemo import ag_groupchat_demo
from demo.CAPAutGenGroupDemo import cap_ag_group_demo
from demo.CAPAutoGenPairDemo import cap_ag_pair_demo
from demo.ComplexActorDemo import complex_actor_demo

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # noqa: E402
sys.path.append(parent_dir)  # noqa: E402

import Config  # noqa: E402
import argparse  # noqa: E402
import DebugLog as DebugLog  # noqa: E402

####################################################################################################

def parse_args():
    # Create a parser for the command line arguments
    parser = argparse.ArgumentParser(description="Demo App")
    parser.add_argument("--log_level", type=int, default=1, help="Set the log level (0-3)")
    # Parse the command line arguments
    args = parser.parse_args()
    # Set the log level
    Config.LOG_LEVEL = args.log_level
    # Print log level string based on names in debug_log.py
    print(f"Log level: {DebugLog.LEVEL_NAMES[args.log_level]}")
    Config.IGNORED_LOG_CONTEXTS.extend(["BROKER"])

####################################################################################################

def main():
    parse_args()
    while True:
        print("Select the demo app to run:")
        print("1. CAP Hello World")
        print("2. CAP Complex Agent (e.g. Name or Quit)")
        print("3. AutoGen Pair")
        print("4. CAP AutoGen Pair")
        print("5. AutoGen GroupChat")
        print("6. CAP AutoGen GroupChat")
        choice = input("Enter your choice (1-6): ")

        if choice == "1":
            simple_actor_demo()
        elif choice == "2":
            complex_actor_demo()
        elif choice == "3":
            ag_demo()
        elif choice == "4":
            cap_ag_pair_demo()
        elif choice == "5":
            ag_groupchat_demo()
        elif choice == "6":
            cap_ag_group_demo()
        else:
            print("Quitting...")
            break


if __name__ == "__main__":
    main()
