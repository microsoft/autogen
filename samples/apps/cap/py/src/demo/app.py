"""
Demo App
"""
import os
import sys

parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(parent_dir)

import Config
import argparse
import time
import DebugLog as DebugLog
from demo.app_agents import (
    FidelityAgent,
    FinancialPlannerAgent,
    PersonalAssistant,
    QuantAgent,
    UserInterfaceAgent,
)
from LocalActorNetwork import LocalActorNetwork
from termcolor import colored
from autogen import (
    GroupChat,
    GroupChatManager,
    AssistantAgent,
    config_list_from_json,
    UserProxyAgent,
)
from ag_adapter.AG2CAP import AG2CAP
from ag_adapter.CAP2AG import CAP2AG

####################################################################################################


def simple_actor_demo():
    """
    Demonstrates the usage of the CAP platform by registering an agent, connecting to other agents,
    sending a message, and performing cleanup operations.
    """
    # CAP Platform

    network = LocalActorNetwork()
    # Register an agent

    time.sleep(0.01)  # Let the network do things
    network.register(UserInterfaceAgent())
    # Tell agents to connect to other agents

    time.sleep(0.01)  # Let the network do things
    network.connect()
    # Get a channel to the agent

    ui_sender = network.lookup_agent(UserInterfaceAgent.cls_agent_name)
    time.sleep(0.01)  # Let the network do things
    # Send a message to the agent

    ui_sender.send_txt_msg("Hello World!")
    time.sleep(0.01)  # Let the network do things
    # Cleanup

    ui_sender.close()
    network.disconnect()


####################################################################################################

####################################################################################################

def complex_actor_demo():
    """
    This function demonstrates the usage of a complex actor system.
    It creates a local actor network, registers various agents,
    connects them, and interacts with a personal assistant agent.
    The function continuously prompts the user for input messages,
    sends them to the personal assistant agent, and terminates
    when the user enters "quit".
    """
    network = LocalActorNetwork()
    # Register agents

    network.register(PersonalAssistant())
    network.register(UserInterfaceAgent())
    network.register(FidelityAgent())
    network.register(FinancialPlannerAgent())
    network.register(QuantAgent())
    # Tell agents to connect to other agents

    network.connect()
    # Get a channel to the personal assistant agent

    pa = network.lookup_agent(PersonalAssistant.cls_agent_name)
    while True:
        time.sleep(0.1)  # Let the network do things
        # Get a message from the user

        msg = input(colored("Enter a message: ", "light_red"))
        # Send the message to the personal assistant agent

        pa.send_txt_msg(msg)
        if msg.lower() == "quit":
            break
    # Cleanup

    pa.close()
    network.disconnect()


####################################################################################################

####################################################################################################

def ag_demo():
    config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")
    assistant = AssistantAgent("assistant", llm_config={"config_list": config_list})
    user_proxy = UserProxyAgent(
        "user_proxy", code_execution_config={"work_dir": "coding"},
        is_termination_msg=lambda x: "TERMINATE" in x.get("content")    )
    user_proxy.initiate_chat(
        assistant, message="Plot a chart of MSFT daily closing prices for last 1 Month."
    )


####################################################################################################

####################################################################################################


def cap_ag_pair_demo():
    config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")
    assistant = AssistantAgent("assistant", llm_config={"config_list": config_list})
    user_proxy = UserProxyAgent(
        "user_proxy", code_execution_config={"work_dir": "coding"},
        is_termination_msg=lambda x: "TERMINATE" in x.get("content")
    )

    # Composable Agent Network adapter

    network = LocalActorNetwork()
    user_proxy_adptr = CAP2AG(
        ag_agent=user_proxy, 
        the_other_name="assistant", 
        init_chat=True, 
        self_recursive=True
    )
    assistant_adptr = CAP2AG(
        ag_agent=assistant, 
        the_other_name="user_proxy", 
        init_chat=False, 
        self_recursive=True
    )
    
    network.register(user_proxy_adptr)
    network.register(assistant_adptr)
    time.sleep(0.01)
    network.connect()
    time.sleep(0.01)

    # Send a message to the user_proxy

    user_proxy = network.lookup_agent("user_proxy")
    time.sleep(0.01)
    user_proxy.send_txt_msg(
        "Plot a chart of MSFT daily closing prices for last 1 Month."
    )

    # Hang around for a while

    while True:
        time.sleep(0.5)
        if not user_proxy_adptr.run and not assistant_adptr.run:
            break
    network.disconnect()
    DebugLog.Info("App", "App Exit")


####################################################################################################

####################################################################################################


def ag_groupchat_demo():
    config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")
    gpt4_config = {
        "cache_seed": 72,
        "temperature": 0,
        "config_list": config_list,
        "timeout": 120,
    }
    user_proxy = UserProxyAgent(
        name="User_proxy",
        system_message="A human admin.",
        code_execution_config={
            "last_n_messages": 2,
            "work_dir": "groupchat",
            "use_docker": False,
        },
        human_input_mode="TERMINATE",
        is_termination_msg=lambda x: "TERMINATE" in x.get("content")
    )
    coder = AssistantAgent(name="Coder", llm_config=gpt4_config)
    pm = AssistantAgent(
        name="Product_manager",
        system_message="Creative in software product ideas.",
        llm_config=gpt4_config,
    )
    groupchat = GroupChat(agents=[user_proxy, coder, pm], messages=[], max_round=12)
    manager = GroupChatManager(groupchat=groupchat, llm_config=gpt4_config)
    user_proxy.initiate_chat(
        manager,
        message="Find a latest paper about gpt-4 on arxiv and find its potential applications in software.",
    )


####################################################################################################

####################################################################################################


def cap_ag_group_demo():
    config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")
    gpt4_config = {
        "cache_seed": 73,
        "temperature": 0,
        "config_list": config_list,
        "timeout": 120,
    }

    user_proxy = UserProxyAgent(
        name="User_proxy",
        system_message="A human admin.",
        is_termination_msg=lambda x: "TERMINATE" in x.get("content"),
        code_execution_config={
            "last_n_messages": 2,
            "work_dir": "groupchat",
            "use_docker": False,
        },
        human_input_mode="TERMINATE",
    )
    coder = AssistantAgent(name="Coder", llm_config=gpt4_config)
    pm = AssistantAgent(
        name="Product_manager",
        system_message="Creative in software product ideas.",
        llm_config=gpt4_config,
    )

    # Composable Agent Network adapter

    network = LocalActorNetwork()
    user_proxy_cap2ag = CAP2AG(
        ag_agent=user_proxy,
        the_other_name="chat_manager",
        init_chat=True,
        self_recursive=False
    )

    coder_cap2ag = CAP2AG(
        ag_agent=coder,
        the_other_name="chat_manager",
        init_chat=False,
        self_recursive=False
    )

    pm_cap2ag = CAP2AG(
        ag_agent=pm,
        the_other_name="chat_manager",
        init_chat=False,
        self_recursive=False
    )
    network.register(user_proxy_cap2ag)
    network.register(coder_cap2ag)
    network.register(pm_cap2ag)

    user_proxy_ag2cap = AG2CAP(network, agent_name=user_proxy.name, agent_description=user_proxy.description)
    coder_ag2cap = AG2CAP(network, agent_name=coder.name, agent_description=coder.description)
    pm_ag2cap = AG2CAP(network, agent_name=pm.name, agent_description=pm.description)
    groupchat = GroupChat(
        agents=[user_proxy_ag2cap, coder_ag2cap, pm_ag2cap], messages=[], max_round=12
    )

    manager = GroupChatManager(groupchat=groupchat, llm_config=gpt4_config)

    manager_cap2ag = CAP2AG(
        ag_agent=manager,
        the_other_name=user_proxy.name,
        init_chat=False,
        self_recursive=True
    )
    network.register(manager_cap2ag)

    time.sleep(0.01)
    network.connect()
    time.sleep(0.01)
    user_proxy_conn = network.lookup_agent(user_proxy.name)
    time.sleep(0.01)
    user_proxy_conn.send_txt_msg(
        "Find a latest paper about gpt-4 on arxiv and find its potential applications in software."
    )

    while True:
        time.sleep(0.5)
        if not user_proxy_cap2ag.run and not coder_cap2ag.run and not pm_cap2ag.run and not manager_cap2ag.run:
            break
        
    network.disconnect()
    DebugLog.Info("App", "App Exit")


####################################################################################################


def parse_args():
    # Create a parser for the command line arguments
    parser = argparse.ArgumentParser(description="Demo App")
    parser.add_argument(
        "--log_level", type=int, default=1, help="Set the log level (0-3)"
    )
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
