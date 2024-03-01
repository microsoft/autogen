import time
import _paths
from autogen import AssistantAgent, config_list_from_json
from autogencap.DebugLog import Info
from autogencap.LocalActorNetwork import LocalActorNetwork
from autogencap.ag_adapter.CAP2AG import CAP2AG


# Starts the Broker and the Assistant. The UserProxy is started separately.
class StandaloneAssistant:
    def __init__(self):
        pass

    def run(self):
        print("Running the StandaloneAssistant")
        config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")
        assistant = AssistantAgent("assistant", llm_config={"config_list": config_list})
        # Composable Agent Network adapter
        network = LocalActorNetwork()
        assistant_adptr = CAP2AG(ag_agent=assistant, the_other_name="user_proxy", init_chat=False, self_recursive=True)
        network.register(assistant_adptr)
        network.connect()

        # Hang around for a while
        try:
            while assistant_adptr.run:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("Interrupted by user, shutting down.")
        network.disconnect()
        Info("StandaloneAssistant", "App Exit")


def main():
    assistant = StandaloneAssistant()
    assistant.run()


if __name__ == "__main__":
    main()
