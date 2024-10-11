#!/usr/bin/env python3 -m pytest

import os
import sys

import pytest

from autogen import ConversableAgent, config_list_from_json
from autogen.formatting_utils import colored

sys.path.append(os.path.join(os.path.dirname(__file__), "../../.."))
from conftest import skip_openai  # noqa: E402

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from test_assistant_agent import KEY_LOC, OAI_CONFIG_LIST  # noqa: E402

try:
    from autogen.agentchat.contrib.capabilities.teachability import Teachability
except ImportError:
    skip = True
else:
    skip = skip_openai


# Specify the model to use by uncommenting one of the following lines.
# filter_dict={"model": ["gpt-4-1106-preview"]}
# filter_dict={"model": ["gpt-4-0613"]}
# filter_dict={"model": ["gpt-3.5-turbo-1106"]}
# filter_dict={"model": ["gpt-3.5-turbo-0613"]}
# filter_dict={"model": ["gpt-4"]}
# filter_dict = {"tags": ["gpt-35-turbo-16k", "gpt-3.5-turbo-16k"]}
filter_dict = {"model": ["gpt-4o-mini"]}


def create_teachable_agent(reset_db=False, verbosity=0):
    """Instantiates a teachable agent using the settings from the top of this file."""
    # Load LLM inference endpoints from an env variable or a file
    # See https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
    # and OAI_CONFIG_LIST_sample
    config_list = config_list_from_json(env_or_file=OAI_CONFIG_LIST, filter_dict=filter_dict, file_location=KEY_LOC)

    # Start by instantiating any agent that inherits from ConversableAgent.
    teachable_agent = ConversableAgent(
        name="teachable_agent",
        llm_config={"config_list": config_list, "timeout": 120, "cache_seed": None},  # Disable caching.
    )

    # Instantiate the Teachability capability. Its parameters are all optional.
    teachability = Teachability(
        verbosity=verbosity,
        reset_db=reset_db,
        path_to_db_dir="./tmp/teachability_db",
        recall_threshold=1.5,  # Higher numbers allow more (but less relevant) memos to be recalled.
    )

    # Now add the Teachability capability to the agent.
    teachability.add_to_agent(teachable_agent)

    return teachable_agent, teachability


def check_agent_response(teachable_agent, user, correct_answer):
    """Checks whether the agent's response contains the correct answer, and returns the number of errors (1 or 0)."""
    agent_response = user.last_message(teachable_agent)["content"]
    if correct_answer not in agent_response:
        print(colored(f"\nTEST FAILED:  EXPECTED ANSWER {correct_answer} NOT FOUND IN AGENT RESPONSE", "light_red"))
        return 1
    else:
        print(colored(f"\nTEST PASSED:  EXPECTED ANSWER {correct_answer} FOUND IN AGENT RESPONSE", "light_cyan"))
        return 0


def use_question_answer_phrasing():
    """Tests whether the teachable agent can answer a question after being taught the answer in a previous chat."""
    print(colored("\nTEST QUESTION-ANSWER PHRASING", "light_cyan"))
    num_errors, num_tests = 0, 0
    teachable_agent, teachability = create_teachable_agent(
        reset_db=True,
        verbosity=0,  # 0 for basic info, 1 to add memory operations, 2 for analyzer messages, 3 for memo lists.
    )  # For a clean test, clear the agent's memory.
    user = ConversableAgent("user", max_consecutive_auto_reply=0, llm_config=False, human_input_mode="NEVER")

    # Prepopulate memory with a few arbitrary memos, just to make retrieval less trivial.
    teachability.prepopulate_db()

    # Ask the teachable agent to do something using terminology it doesn't understand.
    user.initiate_chat(recipient=teachable_agent, message="What is the twist of 5 and 7?")

    # Explain the terminology to the teachable agent.
    user.send(
        recipient=teachable_agent,
        message="Actually, the twist of two or more numbers is their product minus their sum. Try again.",
    )
    num_errors += check_agent_response(teachable_agent, user, "23")
    num_tests += 1

    # Now start a new chat to clear the context, and require the teachable agent to use its new knowledge.
    print(colored("\nSTARTING A NEW CHAT WITH EMPTY CONTEXT", "light_cyan"))
    user.initiate_chat(recipient=teachable_agent, message="What's the twist of 8 and 3 and 2?")
    num_errors += check_agent_response(teachable_agent, user, "35")
    num_tests += 1

    # Wrap up.
    return num_errors, num_tests


def use_task_advice_pair_phrasing():
    """Tests whether the teachable agent can demonstrate a new skill after being taught a task-advice pair in a previous chat."""
    print(colored("\nTEST TASK-ADVICE PHRASING", "light_cyan"))
    num_errors, num_tests = 0, 0
    teachable_agent, teachability = create_teachable_agent(
        reset_db=True,  # For a clean test, clear the teachable agent's memory.
        verbosity=3,  # 0 for basic info, 1 to add memory operations, 2 for analyzer messages, 3 for memo lists.
    )
    user = ConversableAgent("user", max_consecutive_auto_reply=0, llm_config=False, human_input_mode="NEVER")

    # Prepopulate memory with a few arbitrary memos, just to make retrieval less trivial.
    teachability.prepopulate_db()

    # Ask the teachable agent to do something, and provide some helpful advice.
    user.initiate_chat(
        recipient=teachable_agent,
        message="Compute the twist of 5 and 7. Here's a hint: The twist of two or more numbers is their product minus their sum.",
    )
    num_errors += check_agent_response(teachable_agent, user, "23")
    num_tests += 1

    # Now start a new chat to clear the context, and require the teachable agent to use its new knowledge.
    print(colored("\nSTARTING A NEW CHAT WITH EMPTY CONTEXT", "light_cyan"))
    user.initiate_chat(recipient=teachable_agent, message="Please calculate the twist of 8 and 3 and 2.")
    num_errors += check_agent_response(teachable_agent, user, "35")
    num_tests += 1

    # Wrap up.
    return num_errors, num_tests


@pytest.mark.skipif(
    skip,
    reason="do not run if dependency is not installed or requested to skip",
)
def test_teachability_code_paths():
    """Runs this file's unit tests."""
    total_num_errors, total_num_tests = 0, 0

    num_trials = 1  # Set to a higher number to get a more accurate error rate.
    for trial in range(num_trials):
        num_errors, num_tests = use_question_answer_phrasing()
        total_num_errors += num_errors
        total_num_tests += num_tests

        num_errors, num_tests = use_task_advice_pair_phrasing()
        total_num_errors += num_errors
        total_num_tests += num_tests

        print(colored(f"\nTRIAL {trial + 1} OF {num_trials} FINISHED", "light_cyan"))

    if total_num_errors == 0:
        print(colored("\nTEACHABLE AGENT TESTS FINISHED WITH ZERO ERRORS", "light_cyan"))
    else:
        print(
            colored(
                f"\nTEACHABLE AGENT TESTS FINISHED WITH {total_num_errors} / {total_num_tests} TOTAL ERRORS ({100.0 * total_num_errors / total_num_tests}%)",
                "light_red",
            )
        )


@pytest.mark.skipif(
    skip,
    reason="do not run if dependency is not installed or requested to skip",
)
def test_teachability_accuracy():
    """A very cheap and fast test of teachability accuracy."""
    print(colored("\nTEST TEACHABILITY ACCURACY", "light_cyan"))

    num_trials = 10  # The expected probability of failure is about 0.3 on each trial.
    for trial in range(num_trials):
        teachable_agent, teachability = create_teachable_agent(
            reset_db=True, verbosity=0
        )  # For a clean test, clear the agent's memory.
        user = ConversableAgent("user", max_consecutive_auto_reply=0, llm_config=False, human_input_mode="NEVER")

        # Prepopulate memory with a few arbitrary memos, just to make retrieval less trivial.
        teachability.prepopulate_db()

        # Tell the teachable agent something it wouldn't already know.
        user.initiate_chat(recipient=teachable_agent, message="My favorite color is teal.")

        # Now start a new chat to clear the context, and ask the teachable agent about the new information.
        print(colored("\nSTARTING A NEW CHAT WITH EMPTY CONTEXT", "light_cyan"))
        user.initiate_chat(recipient=teachable_agent, message="What's my favorite color?")
        num_errors = check_agent_response(teachable_agent, user, "teal")

        print(colored(f"\nTRIAL {trial + 1} OF {num_trials} FINISHED", "light_cyan"))

        # Exit on the first success.
        if num_errors == 0:
            return

    # All trials failed.
    assert False, "test_teachability_accuracy() failed on all {} trials.".format(num_trials)


if __name__ == "__main__":
    """Runs this file's unit tests from the command line."""
    test_teachability_code_paths()
    test_teachability_accuracy()
