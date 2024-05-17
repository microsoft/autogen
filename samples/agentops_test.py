from typing import Annotated, Literal
import agentops

from autogen import ConversableAgent, UserProxyAgent, config_list_from_json, register_function

Operator = Literal["+", "-", "*", "/"]
agentops.init(tags=["autogen-tool"])


def calculator(a: int, b: int, operator: Annotated[Operator, "operator"]) -> int:
    if operator == "+":
        return a + b
    elif operator == "-":
        return a - b
    elif operator == "*":
        return a * b
    elif operator == "/":
        return int(a / b)
    else:
        raise ValueError("Invalid operator")


def main():
    # Load LLM inference endpoints from an env variable or a file
    # See https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
    # and OAI_CONFIG_LIST_sample.
    # For example, if you have created a OAI_CONFIG_LIST file in the current working directory, that file will be used.
    config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")

    # Create the agent that uses the LLM.
    assistant = ConversableAgent(
        name="Assistant",
        system_message="You are a helpful AI assistant. "
        "You can help with simple calculations. "
        "Return 'TERMINATE' when the task is done.",
        llm_config={"config_list": config_list},
    )

    # The user proxy agent is used for interacting with the assistant agent
    # and executes tool calls.
    user_proxy = ConversableAgent(
        name="User",
        llm_config=False,
        is_termination_msg=lambda msg: msg.get("content") is not None and "TERMINATE" in msg["content"],
        human_input_mode="NEVER",
    )

    assistant.register_for_llm(name="calculator", description="A simple calculator")(calculator)
    user_proxy.register_for_execution(name="calculator")(calculator)

    # Register the calculator function to the two agents.
    register_function(
        calculator,
        caller=assistant,  # The assistant agent can suggest calls to the calculator.
        executor=user_proxy,  # The user proxy agent can execute the calculator calls.
        name="calculator",  # By default, the function name is used as the tool name.
        description="A simple calculator",  # A description of the tool.
    )

    # Let the assistant start the conversation.  It will end when the user types exit.
    user_proxy.initiate_chat(assistant, message="What is (1423 - 123) / 3 + (32 + 23) * 5?")

    agentops.end_session("Success")


if __name__ == "__main__":
    main()


# What is (44232 + 13312 / (232 - 32)) * 5?
