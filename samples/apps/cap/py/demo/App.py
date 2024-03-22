"""
Demo App
"""

import argparse
import _paths
from autogencap.Config import LOG_LEVEL, IGNORED_LOG_CONTEXTS
import autogencap.DebugLog as DebugLog
from SimpleActorDemo import simple_actor_demo
from AGDemo import ag_demo
from AGGroupChatDemo import ag_groupchat_demo
from CAPAutGenGroupDemo import cap_ag_group_demo
from CAPAutoGenPairDemo import cap_ag_pair_demo
from ComplexActorDemo import complex_actor_demo
from RemoteAGDemo import remote_ag_demo

####################################################################################################


def parse_args():
    # Create a parser for the command line arguments
    parser = argparse.ArgumentParser(description="Demo App")
    parser.add_argument("--log_level", type=int, default=1, help="Set the log level (0-3)")
    # Parse the command line arguments
    args = parser.parse_args()
    # Set the log level
    # Print log level string based on names in debug_log.py
    print(f"Log level: {DebugLog.LEVEL_NAMES[args.log_level]}")
    # IGNORED_LOG_CONTEXTS.extend(["BROKER"])


####################################################################################################


def main():
    parse_args()
    while True:
        print("Select the Composable Actor Platform (CAP) demo app to run:")
        print("(enter anything else to quit)")
        print("1. Hello World")
        print("2. Complex Agent (e.g. Name or Quit)")
        print("3. AutoGen Pair")
        print("4. AutoGen GroupChat")
        print("5. AutoGen Agents in different processes")
        choice = input("Enter your choice (1-5): ")

        if choice == "1":
            simple_actor_demo()
        elif choice == "2":
            complex_actor_demo()
        # elif choice == "3":
        #     ag_demo()
        elif choice == "3":
            cap_ag_pair_demo()
        # elif choice == "5":
        #     ag_groupchat_demo()
        elif choice == "4":
            cap_ag_group_demo()
        elif choice == "5":
            remote_ag_demo()
        else:
            print("Quitting...")
            break


if __name__ == "__main__":
    main()
