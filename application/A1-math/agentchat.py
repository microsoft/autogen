from flaml.autogen import AssistantAgent, UserProxyAgent
import flaml
from flaml.autogen.code_utils import UNKNOWN, extract_code, execute_code, infer_lang
from flaml.autogen.math_utils import eval_math_responses, get_answer
from utils import remove_asy_sections
from openai import InvalidRequestError
import time

import signal

def timeout_handler(signum, frame):
    raise Exception("AgentChat Timeout. Need restart.")

class AgentChat:
    def __init__(self, config_list, system_message=None, seed=42, max_consecutive_auto_reply=15, use_cache=True):
        """Initialize AgentChat

        Args:
            seed (int): random seed.
            config_list (list): list of config dicts.
            max_consecutive_auto_reply (int): maximum number of consecutive auto replies.
        """
        llm_config={
            "config_list": config_list,
            "request_timeout": 600,
        }
        if not use_cache:
            llm_config["use_cache"] = use_cache
        else:
            llm_config['seed'] = seed

        # create an AssistantAgent instance named "assistant"
        self.assistant = AssistantAgent(
            name="assistant",
            llm_config=llm_config
        )
        if system_message is not None:
            self.assistant = AssistantAgent(
            name="assistant",
            llm_config=llm_config,
            system_message=system_message,
        )

        print(f"Seed = {seed}", flush=True)
        print(f"Version = {flaml.__version__}", flush=True)
        print(self.assistant.system_message, flush=True)

        # create the UserProxyAgent instance named "user"
        self.user = UserProxyAgent(
            name="user",
            human_input_mode="NEVER",
            is_termination_msg=lambda x: x.get("content", "")
            and (
                x.get("content", "").rstrip().endswith("TERMINATE")
                or x.get("content", "").rstrip().endswith("TERMINATE.")
            ),
            code_execution_config={
                "work_dir": "coding",
                "use_docker": False,  # set to True or image name like "python:3" to use docker
            },
            max_consecutive_auto_reply=max_consecutive_auto_reply,
        )

    def solve_one_problem(self, problem):
        """Solve one problem.

        Args:
            problem (dict): a problem dict. Use problem["problem"] to extract the problem text.
        """
        # reset
        self.assistant.reset()
        self.user.reset()

        # solve
        start = time.time()
        signal.signal(signal.SIGALRM, timeout_handler)
        try:
            signal.alarm(800)
            self.user.initiate_chat(self.assistant, message=problem["problem"])
            signal.alarm(0)
        except Exception as e:
            print(f"Got error: {e}, take it as wrong", flush=True)
        total_time = time.time() - start

        print("**********************************************", flush=True)
        print("**********************************************\n\n", flush=True)

        # extract reply
        response_with_ans = self.assistant._oai_messages[self.user][-1]["content"]
        messages = self.assistant._oai_messages[self.user]
        for j in range(len(messages) - 1, -1, -1):
            if (
                messages[j]["role"] == "assistant"
                and messages[j]["content"].strip() != "TERMINATE"
                and messages[j]["content"].strip() != "TERMINATE."
            ):
                response_with_ans = messages[j]["content"]
                break

        return {
            # must have
            "response_with_ans": response_with_ans,
            "correct_ans": get_answer(problem["solution"]),
            "round": (len(self.assistant._oai_messages[self.user]) - 1) // 2,
            "messages": self.assistant._oai_messages[self.user],
            "time" : total_time
        }
