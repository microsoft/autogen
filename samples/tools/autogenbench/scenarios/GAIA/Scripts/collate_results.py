import os
import json
import re
import argparse
from typing import Tuple


def normalize_answer(a):
    # Lower case
    # Trim (left and right)
    # standardize comma separated values
    # Replace multiple spaces with one space
    # Remove trailing punctuation
    norm_answer = ", ".join(a.strip().split(","))
    norm_answer = re.sub(r"[\.\!\?]+$", "", re.sub(r"\s+", " ", norm_answer))
    return norm_answer.lower()


def collate(results_dir, classify_reasoning_trace=False):
    """
    Collate the results of running GAIA. Print the results in the format accepted by the leaderboard.

    Args:
        results_dir (path): The folder where results were be saved.
    """

    for test_id in os.listdir(results_dir):
        test_path = os.path.join(results_dir, test_id)

        for instance in os.listdir(test_path):
            instance_dir = os.path.join(test_path, str(instance))
            console_log_file = os.path.join(instance_dir, "console_log.txt")

            final_answer = ""
            console_log = ""
            if os.path.isfile(console_log_file):
                with open(console_log_file, "rt", encoding="utf8") as fh:
                    console_log = fh.read()

                    # Trim the console log
                    m = re.search(
                        r"SCENARIO.PY STARTING !#!#(.*)", console_log, re.DOTALL
                    )
                    if m:
                        console_log = m.group(1).strip()

                    # Extract the final answer
                    final_answer = ""
                    m = re.search(r"FINAL ANSWER:(.*?)\n", console_log, re.DOTALL)
                    if m:
                        final_answer = m.group(1).strip()

            expected_answer_file = os.path.join(instance_dir, "expected_answer.txt")
            expected_answer = "NOT PROVIDED !#!#"
            if os.path.isfile(expected_answer_file):
                with open(expected_answer_file, "rt") as fh:
                    expected_answer = fh.read().strip()

            prompt_file = os.path.join(instance_dir, "prompt.txt")
            prompt = None
            if os.path.isfile(prompt_file):
                with open(prompt_file, "rt", encoding="utf8") as fh:
                    prompt = fh.read().strip()

            # Apply approximate string matching
            is_correct = normalize_answer(final_answer) == normalize_answer(expected_answer)

            # Parse the steps
            steps = [s.strip() for s in re.split(r"\-\-\-\-\-\-\-\-+", console_log) if len(s) > 0]

            if classify_reasoning_trace:
                steps = Classify_log.classify_steps(steps)

            # save json to file
            js_str = json.dumps(
                {
                    "task_id": test_id,
                    "trial": instance,
                    "question": prompt,
                    "is_correct": is_correct,
                    "model_answer": final_answer,
                    "expected_answer": expected_answer,
                    "length_of_trace": len(steps),
                    "reasoning_trace": steps,
                },
                indent=4,
            )

            with open(os.path.join(instance_dir, "results.json"), "wt") as fh:
                fh.write(js_str)
            yield steps


class Classify_log:
    @staticmethod
    def basic_clean(step: str) -> list[str]:
        step_lines = step.split("\n")
        step_lines = list(filter(None, step_lines))
        return step_lines

    find_string = lambda lst, substring: next((s for s in lst if substring in s), None)

    @staticmethod
    def process_lines(steps: list[str], prev_validated_steps) -> Tuple[str, dict[str, str]]:
        if any("orchestrator (thought)" in line for line in steps):
            if any("We aren't making progress. Let's reset." in line for line in steps):
                return "RESET", {}
            # get actual json object of next_step
            joined = "\n".join(steps[1:])
            try:
                parsed_json = json.loads(joined)
                return "NEXT_STEP", parsed_json
            except json.JSONDecodeError:
                return "RUNTIME_ERROR", {}
        elif any("orchestrator (to " in line for line in steps):
            assert prev_validated_steps[-1][1] != {}, prev_validated_steps[-1]
            assert "next_speaker" in prev_validated_steps[-1][1], (steps, prev_validated_steps[-1][1])
            next_speaker = prev_validated_steps[-1][1]["next_speaker"]["answer"]
            if next_speaker not in steps[0]:
                return "DELEGATE_TO_AGENT_MISMATCH", {}

            match = Classify_log.find_string(steps, "orchestrator (to").split(" ")
            return "DELEGATE_TO_AGENT", {"from": match[0], "to": match[2].split(")")[0]}
        elif any("(to orchestrator)" in line for line in steps):
            match = Classify_log.find_string(steps, "(to orchestrator)").split(" ")
            return "RESPONSE_FROM_AGENT", {"from": match[0], "to": match[2].split(")")[0]}
        elif any("FINAL ANSWER" in line for line in steps):
            return "FINAL_ANSWER", {}
        else:
            return "NO_MATCH", {}

    @staticmethod
    def classify_steps(steps):
        current_step = "INIT"
        classified_steps = []

        stall_count = 0
        for step in steps:
            step_split = Classify_log.basic_clean(step)
            if any("orchestrator (to computer_terminal)" in line for line in step_split):
                if any("TERMINATE" in line for line in step_split):
                    match = Classify_log.find_string(step_split, "orchestrator (to").split(" ")
                    current_step = "ORCH_TERMINATE"
                    classified_steps.append((current_step, {"from": match[0], "to": match[2]}, step_split))

            if current_step == "INIT":
                assert len(classified_steps) == 0
                assert any("powershell" in line for line in step_split), step_split
                assert len(step_split) >= 3, step_split
                if any("MLM Prompt" in line for line in step_split):
                    current_step = "MLM_INIT"
                classified_steps.append((current_step, {}, step_split))
                current_step = "FIRST_PLAN"
            elif current_step == "FIRST_PLAN":
                stall_count = 0
                if not any("We are working" in line for line in step_split):
                    classified_steps.append(("NO_MATCH", {}, step_split))
                    continue
                classified_steps.append((current_step, {}, step_split))
                current_step = "PROCESS_LINE"
            elif current_step == "PROCESS_LINE":
                current_step, parsed = Classify_log.process_lines(step_split, prev_validated_steps=classified_steps)

                if parsed != {}:
                    # check for termination
                    if "is_request_satisfied" in parsed:
                        if parsed["is_request_satisfied"]["answer"]:
                            current_step += "_TERMINATE"
                    # check for stall
                    if "is_progress_being_made" in parsed:
                        if parsed["is_progress_being_made"]["answer"]:
                            current_step += "_PROGRESS"
                            stall_count -= 1
                        else:
                            current_step += "_NO_PROGRESS"
                            stall_count += 1
                        stall_count = max(0, stall_count)
                    parsed["stall_count"] = stall_count

                classified_steps.append((current_step, parsed, step_split))
                if "NEXT_STEP" in current_step:
                    current_step = "NEXT_STEP"
                if current_step == "RESET":
                    if stall_count != 3:
                        classified_steps.append(
                            (
                                "STALL_COUNT_MISMATCH?",
                                {"desc": f"stall_count should be 3 but its {stall_count}"},
                                step_split,
                            )
                        )
                    current_step = "FIRST_PLAN"
                else:
                    current_step = "PROCESS_LINE"

        return classified_steps


###############################################################################
if __name__ == "__main__":
    script_path = os.path.realpath(__file__)
    script_name = os.path.basename(script_path)
    script_dir = os.path.dirname(script_path)

    parser = argparse.ArgumentParser(
        description=f"""
{script_name} will collate the results of the GAIA scenarios into the jsonl format that can be submit to AgentEval.
""".strip(),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "scenario",
        help="Path to the scenario results.",
    )
    args = parser.parse_args()
    collate(args.scenario)
