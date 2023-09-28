from autogen import AssistantAgent, UserProxyAgent
from openai import InvalidRequestError
import signal

def timeout_handler(signum, frame):
    raise Exception("Checkout Timeout. Need manual check.")

class AnswerChecker:
    def __init__(self, config_list) -> None:
        # define answer checker chat
        self.answer_checker = AssistantAgent(
            name="checker",
            llm_config={
                "seed": 42,
                "config_list": config_list,
                "request_timeout": 600,
            },
            system_message="""You are a helpful AI assistant. You will use your coding and language skills to verify the answer.
    You are given:
        1. A problem.
        2. A reply with the answer to the problem.
        3. A ground truth answer.
    Please do the following:
    1. Extract the answer in the reply: "The answer is <answer extracted>".
    2. Check whether the answer in the reply matches the ground truth answer.
        - The answer doesn't need to be in the exact format, but whether they have the same concept. For example, using "and" and "," might be the same.
        - When comparison is not obvious (for example, 3*\\sqrt(6) and 7.348), you may write code to check the answer and wait for the user to execute the code.
        - You should also note what the problem is asking for. For example, if the problem is asking to simplify a fraction to rational form, but the answer is in decimal form, you should mark the answer as incorrect even if they are the same number.
    3. After everything is done, please choose a reply from the following options:
        - "The answer is correct."
        - "The answer is approximated but should be correct. Correct Answer: <ground truth answer> | Answer extracted: <answer extracted>."
        - "The answer is incorrect. Correct Answer: <ground truth answer> | Answer extracted: <answer extracted>."
        - "The reply doesn't contain an answer." """,
        )

        self.checker_proxy = UserProxyAgent(
            name="checker_proxy",
            human_input_mode="NEVER",
            code_execution_config={
                "work_dir": "coding",
                "use_docker": False,  # set to True or image name like "python:3" to use docker
            },
            max_consecutive_auto_reply=5,
            is_termination_msg=lambda x: x.get("content", "").lower()
            and (
                "the answer is correct" in x.get("content", "").lower()
                or "the answer is incorrect" in x.get("content", "").lower()
                or "the reply doesn't contain an answer" in x.get("content", "").lower()
                or "the answer is approximated but should be correct" in x.get("content", "").lower()
            ),
        )

    def check_answer(self, problem, reply_with_answer, ground_truth_answer):
        """Check answer.
        Args:
            problem (str): the problem text.
            reply_with_answer (str): the reply with answer.
            ground_truth_answer (str): the ground truth answer.
        Returns:
            (dict): the result dict.
        """
        # check answer
        

        message_to_check = (
            f"Problem: {problem}\n\nReply: {reply_with_answer}\n\nGround truth answer: {ground_truth_answer}"
        )
        self.checker_proxy.reset()
        self.answer_checker.reset()

        signal.signal(signal.SIGALRM, timeout_handler)
        try:
            signal.alarm(300)
            self.checker_proxy.initiate_chat(self.answer_checker, message=message_to_check)
            signal.alarm(0)
        except Exception as e:
            print(f"Got error: {e}, take it as wrong", flush=True)
            self.answer_checker._oai_messages[self.checker_proxy].append({"content": "The answer needs manual check.", "role": 'assistant.'})
            

        # record result
        check_result = self.answer_checker._oai_messages[self.checker_proxy][-1]["content"].lower()
        return {
            "check_result": check_result,
            "is_correct": "the answer is correct" in check_result
            or "the answer is approximated but should be correct" in check_result,
        }
