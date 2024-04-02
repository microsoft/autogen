import _paths
import time
from autogen import AssistantAgent, config_list_from_json
from autogencap.LocalActorNetwork import LocalActorNetwork
from autogencap.ag_adapter.agent import Agent
from autogencap.Config import IGNORED_LOG_CONTEXTS

# Filter out some Log message contexts
IGNORED_LOG_CONTEXTS.extend(["BROKER"])

# Starts the Broker and the Assistant. The UserProxy is started separately.
def main():
    # Standard AutoGen
    config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")
    # Standard AutoGen
    assistant = AssistantAgent("assistant", llm_config={"config_list": config_list})
    
    # Wrap AutoGen Agent in CAP
    cap_assistant = Agent(assistant)
    # Create the message bus
    network = LocalActorNetwork()
    # Add the assistant to the message bus
    cap_assistant.register(network)
    # Start message processing
    network.connect()
    
    # Wait for the assistant to finish
    wait_for_agent_to_finish(cap_assistant)
    # Cleanup
    network.disconnect()

def wait_for_agent_to_finish(agent):
    try:
        while agent.running():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Interrupted by user, shutting down.")

if __name__ == "__main__":
    main()