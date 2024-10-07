import os
import sys
import re
from agbench.tabulate_cmd import default_tabulate
import json
import pandas as pd
import sqlite3
import glob
import numpy as np
sys.path.append(os.path.dirname(__file__))

from assistantbench_evaluator import question_scorer

EXCLUDE_DIR_NAMES = ["__pycache__"]


def normalize_answer(a):
    # Lower case
    # Trim (left and right)
    # standardize comma separated values
    # Replace multiple spaces with one space
    # Remove trailing punctuation
    norm_answer = ", ".join(a.strip().lower().split(","))
    norm_answer = re.sub(r"[\.\!\?]+$", "", re.sub(r"\s+", " ", norm_answer))
    return norm_answer


def scorer(instance_dir):
    # Read the expected answer
    expected_answer_file = os.path.join(instance_dir, "expected_answer.txt")
    if not os.path.isfile(expected_answer_file):
        return None

    expected_answer = None
    with open(expected_answer_file, "rt") as fh:
        expected_answer = fh.read().strip()

    # Read the console
    console_log_file = os.path.join(instance_dir, "console_log.txt")
    if not os.path.isfile(console_log_file):
        return None

    console_log = ""
    with open(console_log_file, "rt") as fh:
        console_log = fh.read()

        final_answer = None
        m = re.search(r"FINAL ANSWER:(.*?)\n", console_log, re.DOTALL)
        if m:
            final_answer = m.group(1).strip()

        # Missing the final answer line
        if final_answer is None:
            return None
        # get accuracy from assistantbench util, no normalization done for accuracy
        accuracy = question_scorer(final_answer, expected_answer)
        n_ex = normalize_answer(expected_answer)
        n_final = normalize_answer(final_answer)
        return (accuracy, n_ex, n_final)


def get_number_of_chat_messages(chat_messages_dir):
    result = 0
    for file in glob.glob(f"{chat_messages_dir}/*_messages.json"):
        with open(file, "r") as f:
            content = json.load(f)
            for agent, messages in content.items():
                result += len(messages)
    return result


def main(args):
    parsed_args, all_results = default_tabulate(args, scorer=scorer)
    excel_path = parsed_args.excel

    if excel_path:
        excel_dir = os.path.dirname(excel_path) or "."
        if not os.path.exists(excel_dir):
            os.makedirs(excel_dir, exist_ok=True)

        if not excel_path.endswith((".xlsx", ".xls")):
            excel_path += ".xlsx"

        runlogs = (
            parsed_args.runlogs
            if parsed_args.runlogs.endswith("/")
            else parsed_args.runlogs + "/"
        )

        if os.path.isdir(runlogs):
            task_ids = sorted(
                [
                    task_id
                    for task_id in os.listdir(runlogs)
                    if task_id not in EXCLUDE_DIR_NAMES
                ],
                key=lambda s: os.path.getmtime(os.path.join(parsed_args.runlogs, s)),
            )
        else:
            raise ValueError("please input a valid directory to tabulate result")

        trials = (
            sorted(os.listdir(f"{runlogs}{task_ids[0]}"), key=lambda x: int(x))
            if len(task_ids) > 0
            else []
        )
        dbnames = [
            [f"{runlogs}{task_id}/{trial}/telemetry.db" for task_id in task_ids]
            for trial in trials
        ]

        query = """
            SELECT cost, session_id, response, start_time, end_time
            FROM (
                SELECT invocation_id, cost, session_id, response, start_time, end_time,
                    ROW_NUMBER() OVER (PARTITION BY invocation_id ORDER BY start_time) as rn
                FROM chat_completions
            )
            WHERE rn = 1;
        """

        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            for trial_index, each_trial in enumerate(dbnames):
                result_df = pd.DataFrame(
                    columns=[
                        "id",
                        "status",
                        "expected_answer",
                        "final_answer",
                        "cost",
                        "latency",
                        "num_of_llm_requests",
                        "num_of_chat_messages",
                        "prompt_tokens",
                        "completion_tokens",
                        "total_tokens",
                        "model",
                    ]
                )

                result_df_type_mapping = {
                    "id": str,
                    "status": bool,
                    "expected_answer": str,
                    "final_answer": str,
                    "cost": float,
                    "latency": float,
                    "num_of_llm_requests": int,
                    "num_of_chat_messages": int,
                    "prompt_tokens": int,
                    "completion_tokens": int,
                    "total_tokens": int,
                }

                for dbname, scorer_results in zip(each_trial, all_results):
                    task_id = scorer_results[0]
                    scorer_result = scorer_results[trial_index + 1]

                    status, expected_answer, final_answer = (
                        scorer_result if scorer_result else (False, "", "")
                    )

                    con = sqlite3.connect(dbname)

                    # TODO: if large amount of data, add chunksize
                    telemetry_df = pd.read_sql_query(query, con)

                    earliest_starttime = pd.to_datetime(
                        telemetry_df["start_time"], format="%Y-%m-%d %H:%M:%S.%f"
                    ).min()
                    latest_endtime = pd.to_datetime(
                        telemetry_df["end_time"], format="%Y-%m-%d %H:%M:%S.%f"
                    ).max()

                    num_of_chat_messages = get_number_of_chat_messages(
                        chat_messages_dir=os.path.dirname(dbname)
                    )
                    result = {
                        "id": task_id,
                        "status": status,
                        "expected_answer": expected_answer,
                        "final_answer": final_answer,
                        "cost": telemetry_df["cost"].sum(),
                        "latency": (
                            latest_endtime - earliest_starttime
                        ).total_seconds(),
                        "num_of_llm_requests": len(telemetry_df),
                        "num_of_chat_messages": num_of_chat_messages,
                        "prompt_tokens": telemetry_df["response"]
                        .apply(
                            lambda x: json.loads(x)["usage"]["prompt_tokens"]
                            if "usage" in json.loads(x)
                            and "prompt_tokens" in json.loads(x)["usage"]
                            else 0
                        )
                        .sum(),
                        "completion_tokens": telemetry_df["response"]
                        .apply(
                            lambda x: json.loads(x)["usage"]["completion_tokens"]
                            if "usage" in json.loads(x)
                            and "completion_tokens" in json.loads(x)["usage"]
                            else 0
                        )
                        .sum(),
                        "total_tokens": telemetry_df["response"]
                        .apply(
                            lambda x: json.loads(x)["usage"]["total_tokens"]
                            if "usage" in json.loads(x)
                            and "total_tokens" in json.loads(x)["usage"]
                            else 0
                        )
                        .sum(),
                        "model": telemetry_df["response"]
                        .apply(
                            lambda x: json.loads(x)["model"]
                            if "model" in json.loads(x)
                            else ""
                        )
                        .unique(),
                    }

                    result_df = result_df.astype(result_df_type_mapping)
                    result_df = pd.concat(
                        [result_df, pd.DataFrame([result])], ignore_index=True
                    )
                result_df.to_excel(
                    writer, sheet_name=f"trial_{trial_index}", index=False
                )


if __name__ == "__main__" and __package__ is None:
    main(sys.argv)
