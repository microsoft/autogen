import signal
from autogen import ConversableAgent, config_list_from_json, RemoteAgent, Receiver


def main():
    def signal_handler(sig, frame):
        print("Continuing.")

    signal.signal(signal.SIGINT, signal_handler)
    # Load LLM inference endpoints from an env variable or a file
    # See https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
    # and OAI_CONFIG_LIST_sample.
    # For example, if you have created a OAI_CONFIG_LIST file in the current working directory, that file will be used.
    config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")

    receiver = Receiver(port=45553)

    # Create the agent that uses the LLM.
    rajans_cal = ConversableAgent(
        "rajans_cal",
        llm_config={"config_list": config_list},
        system_message="You are a calendar assistant for Rajan. Your goal is to work with the other agent to find a meeting time that works for both participants. Rajan has 1 hour openings at 10AM, 1PM and 4PM. He has given you the agency to confirm the first time slot where we are both available, you don't need me to check.",
    )
    jacks_cal = RemoteAgent("jacks_cal", host="localhost", port=45554)

    receiver.register_agent(rajans_cal)
    receiver.register_agent(jacks_cal)

    receiver.start()

    rajans_cal.initiate_chat(jacks_cal, message="Please find a time for Rajan to meet with Jack.")

    print("Waiting for control+c")
    signal.pause()
    receiver.stop()


if __name__ == "__main__":
    main()
