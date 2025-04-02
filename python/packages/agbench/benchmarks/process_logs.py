"""
Credits: Hussein Mozannar
"""

import os
import re
import json
import glob
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO)


def process_logs(logs_path, single_benchmark=False):
    """
    logs_path: str, path to the logs directory, containing subdirectories for each benchmark subset
    returns: pandas DataFrame with all the logs processed
    """
    # check if logs_path exists
    if not os.path.exists(logs_path):
        raise FileNotFoundError(
            f"Path {logs_path} does not exist, need to download logs, extract them into one common folder"
        )
    if single_benchmark:
        # subset should be a list with single folder which is the last part of the path
        subsets = [logs_path.split("/")[-1]]
        logs_path = "/".join(logs_path.split("/")[:-1])

    else:
        subsets = os.listdir(logs_path)
    results = []
    for subset in subsets:
        # check if folder is not empty
        if not os.listdir(os.path.join(logs_path, subset)) or subset == ".DS_Store" or subset == "__MACOSX":
            continue
        benchmark_name = subset.split("_")[0]
        instances = [
            f
            for f in os.listdir(os.path.join(logs_path, subset))
            if os.path.isdir(os.path.join(logs_path, subset, f))
            and os.path.exists(os.path.join(logs_path, subset, f, "0"))
        ]
        logging.info(f"Processing {subset} with {len(instances)} instances")
        for instance in instances:
            instance_dir_path = os.path.join(logs_path, subset, instance, "0")
            try:
                correct, expected_answer, final_answer = scorer(instance_dir_path, benchmark_name)
            except Exception as e:
                logging.error(f"Error processing {instance_dir_path}: {e}")
                continue
            messages = get_message_logs(instance_dir_path)
            results.append(
                {
                    "benchmark": benchmark_name,
                    "subset_benchmark": subset,
                    "instance": instance,
                    "task_information": get_task_information(instance_dir_path, benchmark_name),
                    "expected_answer": expected_answer,
                    "final_answer": final_answer,
                    "correct": correct,
                    "stalled": did_agent_stall(instance_dir_path),
                    "num_messages": len(messages),
                    "messages": messages,
                    "progress_not_being_made": is_progress_not_being_made(instance_dir_path),
                }
            )
    df_logs = pd.DataFrame(results)
    return df_logs


def normalize_answer(a):
    """
    Taken from custom_tabulate.py in the WebArena benchmark, given an answer, returns the normalized answer.
    Operations: lower case, trim, standardize comma separated values, replace multiple spaces with one space, remove trailing punctuation
    a: str, answer
    returns: str, normalized answer
    """
    norm_answer = ", ".join(a.strip().lower().split(","))
    norm_answer = re.sub(r"[\.\!\?]+$", "", re.sub(r"\s+", " ", norm_answer))
    return norm_answer


def scorer(instance_dir, benchmark_name):
    """
    Returns results based on the benchmark name and the instance directory.

    benchmark_name: str, the name of the benchmark, either "gaia" or "webarena"
    instance_dir: str, path to the instance directory
    returns: tuple, (bool, str, str) or None, depending on the benchmark
    """

    if benchmark_name == "gaia" or benchmark_name == "assistant":
        # Read the expected answer
        expected_answer_file = os.path.join(instance_dir, "expected_answer.txt")
        if not os.path.isfile(expected_answer_file):
            return None

        with open(expected_answer_file, "rt") as fh:
            expected_answer = fh.read().strip()

        # Read the console log
        console_log_file = os.path.join(instance_dir, "console_log.txt")
        if not os.path.isfile(console_log_file):
            return None

        with open(console_log_file, "rt") as fh:
            console_log = fh.read()
            final_answer = None
            m = re.search(r"FINAL ANSWER:(.*?)\n", console_log, re.DOTALL)
            if m:
                final_answer = m.group(1).strip()

            if final_answer is None:
                return None
            not_normalized_final = final_answer

            n_ex = normalize_answer(expected_answer)
            n_final = normalize_answer(final_answer)
            return (n_ex != "" and n_ex == n_final), n_ex, not_normalized_final

    elif benchmark_name == "webarena":
        # Read the console log
        console_log_file = os.path.join(instance_dir, "console_log.txt")
        if not os.path.isfile(console_log_file):
            return None

        with open(console_log_file, "rt") as fh:
            console_log = fh.read()
            final_score = None
            m = re.search(r"FINAL SCORE:(.*?)\n", console_log, re.DOTALL)
            if m:
                final_score = m.group(1).strip()

            if final_score is None:
                return None
            else:
                return float(final_score) > 0, "", ""

    else:
        raise ValueError(f"Unsupported benchmark_name: {benchmark_name}")


def get_number_of_chat_messages(chat_messages_dir):
    # Count the number of chat messages in the chat_messages_dir
    result = 0
    for file in glob.glob(f"{chat_messages_dir}/*_messages.json"):
        with open(file, "r") as f:
            content = json.load(f)
            for agent, messages in content.items():
                result += len(messages)
    return result


def did_agent_stall(instance_dir):
    # Check if the agent stalled
    log_file_path = os.path.join(instance_dir, "log.jsonl")
    if not os.path.isfile(log_file_path):
        return None
    # Stalled.... Replanning...
    with open(log_file_path, "r") as f:
        for line in f:
            if "Stalled.... Replanning..." in line:
                return True
    return False


def get_message_logs(instance_dir):
    # Read the log file and return the messages
    log_file_path = os.path.join(instance_dir, "log.jsonl")
    if not os.path.isfile(log_file_path):
        return None
    messages = []
    # for each line, convert to dict, check if it has a message and source key, and append to messages
    with open(log_file_path, "r") as f:
        for line in f:
            line_dict = json.loads(line)
            if "message" in line_dict and "source" in line_dict:
                messages.append(line_dict)
    return messages


def get_task_information(instance_dir, benchmark_name):
    # Read the task information from the log file
    if benchmark_name == "gaia" or benchmark_name == "assistant":
        prompt_file = os.path.join(instance_dir, "prompt.txt")
        if not os.path.isfile(prompt_file):
            return None
        with open(prompt_file, "r") as f:
            return f.read().strip()
    elif benchmark_name == "webarena":
        task_prompt_file = os.path.join(instance_dir, "task_prompt.json")
        if not os.path.isfile(task_prompt_file):
            return None
        with open(task_prompt_file, "r") as f:
            return json.load(f)["intent"]
    else:
        raise ValueError(f"Unsupported benchmark_name: {benchmark_name}")


def is_progress_not_being_made(instance_dir):
    # if at any point in the log, progress is not being made, return True
    pattern = r'"is_progress_being_made": \{\s+"reason": ".*?",\s+"answer": false\s+\}'
    log_file_path = os.path.join(instance_dir, "log.jsonl")
    if not os.path.isfile(log_file_path):
        return None
    with open(log_file_path, "r") as f:
        for line in f:
            line_dict = json.loads(line)
            if (
                "source" in line_dict
                and line_dict["source"] == "Orchestrator (thought)"
                and "Updated Ledger:" in line_dict["message"]
                and re.search(pattern, line_dict["message"])
            ):
                return True
    return False
