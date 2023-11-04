import argparse
import json
import os

import autogen
from autogen import config_list_from_json

RESULT_DIR = "sample_data/results"

CONFIG_LIST = config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={"model": ["gpt-4"]},
)

EXAMPLE_CODES = [
    ("TASK-REQUEST", "The messages specifies a task that needs to be completed"),
    ("SUGGESTING-CODING", "The message is suggesting code"),
    ("CODE-EXECUTION", "The message contains results after executing a code"),
    ("EXECUTION-ERROR", "The message is show any errors that happended during code execution"),
    ("TASK-COMPLETION", "The message indicates that a task was completed"),
]


def annotate_message(message: str, codes=None):
    prompt = f"""You are an expert at qualitative analysis of text documents.


Given a message exchanged between two agents, perform
qualitative coding with the following steps: Read the message
to understand the context. Apply descriptive coding to categorize each
message’s content. Implement interpretive coding to identify underlying
themes and intentions.

Only respond with 10 command separated codes.
Use the following codes but feel free to suggest new codes if you really need to:
{EXAMPLE_CODES}

Message:
{message}
 """

    if codes is not None:
        prompt = f"""Which of the following codes apply to the message:
codes: {codes}
message: {message}

Only respond with the codes that apply. Codes should be separated by commas.
"""
    # print(prompt)

    response = autogen.Completion.create(config_list=CONFIG_LIST, prompt=prompt)
    return response["choices"][0]["message"]["content"]


def narrow_codes(initial_annotation_results: str):
    """
    Given the initial annotations, narrow down the codes to a discrete set.
    """
    prompt = f"""You are an expert at qualitative coding.

Reflect on the initial annotations and then
respond with a list of (at max 5) comma separate list of codes.

{initial_annotation_results}
"""
    response = autogen.Completion.create(config_list=CONFIG_LIST, prompt=prompt)
    return response["choices"][0]["message"]["content"]


def profile_conversation(assistant_msgs, viz_path=None):
    """
    Given a list of assistant messages, profile the conversation.
    """

    # Loop over the messages and annotate each of them
    initial_annotation_results = ""

    for agent, msgs in assistant_msgs.items():
        for msg in msgs:
            role, content = msg["role"], msg["content"]
            annotation = annotate_message(content)

            initial_annotation_results += f"{role}: {annotation}\n"

        print("Initial Coding:")
        print(initial_annotation_results)

        # decide on a discrete set of codes using the initial annotations
        final_codes = narrow_codes(initial_annotation_results)
        print("Final codes:")
        print(final_codes)

        print("\nFinal Coding:")
        for msg in msgs:
            role, content = msg["role"], msg["content"]
            annotation = annotate_message(content, codes=final_codes)
            # print(f"{role}: {annotation}\n----\n{content}\n----\n\n")
            print(f"{role}: {annotation}")


def main():
    parser = argparse.ArgumentParser(description="Profile a conversation between AutoGen agents.")
    parser.add_argument("jsonl_path", type=str, help="Path to a scenarios JSON-L file.")
    args = parser.parse_args()

    with open(args.jsonl_path, "r") as f:
        for line in f:
            scenario = json.loads(line)
            # Do something with the data

            scenario_template = scenario["template"][:-3]
            scenario_id = scenario["id"]

            assistant_msgs_path = os.path.join(
                RESULT_DIR, scenario_template, scenario_id, "0", "assistant_messages.json"
            )
            with open(assistant_msgs_path, "r") as f:
                text = f.read()
                assistant_msgs = json.loads(text)
                profile_conversation(assistant_msgs, viz_path="profile.png")
            break


if __name__ == "__main__":
    main()
