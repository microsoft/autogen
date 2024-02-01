import copy
import autogen
from textwrap import dedent
from autogen.agentchat import Agent
from autogen.agentchat.contrib.math_user_proxy_agent import MathUserProxyAgent
from autogen.code_utils import extract_code, UNKNOWN, infer_lang
from autogen.math_utils import get_answer
from typing import Any, Dict, List, Optional, Union
from openai import (
    BadRequestError,
)


def is_termination_msg_mathchat(message):
    """Check if a message is a termination message."""
    if isinstance(message, dict):
        message = message.get("content")
        if message is None:
            return False
    cb = extract_code(message)
    contain_code = False
    for c in cb:
        if c[0] == "python" or c[0] == "wolfram":
            contain_code = True
            break
    if message.rstrip().find("TERMINATE") >= 0 and not contain_code:
        return True

    return (
            not contain_code
            and get_answer(message) is not None
            and get_answer(message) != ""
    )


class MathUserProxy(MathUserProxyAgent):
    MAX_CONSECUTIVE_AUTO_REPLY = 12

    DEFAULT_REPLY = "Continue. Please call other experts to keep solving the problem. (If you get to the answer, put it in \\boxed{}.)"

    PROMPTS = dedent("""Let's solve a math problem step by step with your math expert friends!
If you get to the answer, remember to put it in \\boxed{}. Also, remember to select the "math_problem_solving_assistant" as the speaker to let this person know when everything is done.
Problem: 
""")

    def __init__(
            self,
            name: Optional[str] = "MathChatAgent",
            human_input_mode: Optional[str] = "NEVER",
            default_auto_reply: Optional[Union[str, Dict, None]] = DEFAULT_REPLY,
            use_py=True,
            max_invalid_q_per_step=1,
            is_termination_msg=is_termination_msg_mathchat,
            **kwargs,
    ):
        super().__init__(
            name=name,
            human_input_mode=human_input_mode,
            default_auto_reply=default_auto_reply,
            max_invalid_q_per_step=max_invalid_q_per_step,
            is_termination_msg=is_termination_msg,
            **kwargs,
        )
        del self._reply_func_list[2]
        self.register_reply([Agent, None], MathUserProxy._generate_math_reply, position=4)
        del self._reply_func_list[3]
        self.register_reply(trigger=autogen.ConversableAgent,
                            reply_func=MathUserProxy.generate_function_call_reply, position=3)
        self.register_reply(trigger=autogen.ConversableAgent,
                            reply_func=MathUserProxy._check_final_result, position=1)

        self.max_function_call_trial = 3
        self.query = None
        self.answer = None
        self.use_py = use_py

        self.function_statistic = None

    def _generate_math_reply(
            self,
            messages: Optional[List[Dict]] = None,
            sender: Optional[Agent] = None,
            config: Optional[Any] = None,
    ):
        """Generate an auto reply."""
        if messages is None:
            messages = self._oai_messages[sender]
        message = messages[-1]
        message = message.get("content", "")
        code_blocks = extract_code(message)

        if len(code_blocks) == 1 and code_blocks[0][0] == UNKNOWN:
            # no code block is found, lang should be `UNKNOWN``
            return True, self._default_auto_reply
        is_success, all_success = True, True
        reply = ""
        for code_block in code_blocks:
            lang, code = code_block
            if not lang:
                lang = infer_lang(code)
            if lang == "python":
                output, is_success = self.execute_one_python_code(code)
            elif lang == "wolfram":
                output, is_success = self.execute_one_wolfram_query(code)
            else:
                output = "Error: Unknown language."
                is_success = False

            reply += output + "\n"
            if not is_success:
                all_success = False
                self._valid_q_count -= 1  # count invalid queries

        reply = f"Your Python code execution result is: {reply.strip()}"

        return True, reply

    def generate_function_call_reply(
            self,
            messages: Optional[List[Dict]] = None,
            sender: Optional[autogen.ConversableAgent] = None,
            config: Optional[Any] = None,
    ) -> tuple[bool, dict[str, str]] | tuple[bool, str] | tuple[bool, None]:
        """Generate a reply using function call."""
        if messages is None:
            messages = self._oai_messages[sender]
        message = messages[-1]
        if "function_call" in message:
            is_exec_success, func_return = self.execute_function(message["function_call"])
            # update function_call statistic
            func_name = message["function_call"].get("name", "")
            if self.function_statistic is None:
                self.function_statistic = {}
            if func_name not in self.function_statistic.keys():
                self.function_statistic[func_name] = False
            if is_exec_success:
                self.max_function_call_trial = 3
                self.function_statistic[func_name] = True
                return True, func_return
            else:
                if self.max_function_call_trial == 0:
                    error_message = func_return["content"]
                    self.logs["is_correct"] = 0
                    self.max_function_call_trial = 3
                    return True, "The func is executed failed many times. " + error_message + ". Please directly reply me with TERMINATE. We need to terminate the conversation."
                else:
                    revise_prompt = "You may make a wrong function call (It may due the arguments you provided doesn't fit the function arguments like missing required positional argument). \
                    If you think this error occurs due to you make a wrong function arguments input and you could make it success, please try to call this function again using the correct arguments. \
                    Otherwise, the error may be caused by the function itself. Please directly reply me with TERMINATE. We need to terminate the conversation. "
                    error_message = func_return["content"]
                    return True, "The func is executed failed." + error_message + revise_prompt
        return False, None

    def initiate_chat(
        self,
        recipient,
        message: dict = None,
        silent: Optional[bool] = False,
        **context,
    ):
        self.query = message
        problem = f"{message['question']}\nPlease solve the problem step by step (do not over-divide the steps)."

        answer = message['answer']
        if not isinstance(answer, str):
            answer = str(answer)
        if "." in answer:
            answer = str(float(answer))
        if answer.endswith('.0') or answer.endswith('.00'):
            answer = answer[:-2]
        if "/" in answer:
            answer = answer.split('/')
            answer = str(int(answer[0]) / int(answer[1]))
            answer = str(float(answer))
        answer = answer.replace(',', '')
        self._answer = answer
        self.logs = {}
        self._prepare_chat(recipient, True)

        error_message = None

        try:
            prompt = self.PROMPTS + problem
            self.send(prompt, recipient, silent=silent)
        except BadRequestError as e:
            error_message = str(e)
            self.logs["is_correct"] = 0
            print("error information: {}".format(error_message))

        chat_history = []
        key = list(self.chat_messages.keys())[0]
        chat_messages = self.chat_messages[key]
        for item in chat_messages:
            chat_history.append(item)
        if error_message is not None:
            chat_history.append(error_message)
        chat_history.append({
            "correct_answer": answer,
            "is_correct": self.logs.get("is_correct", 0)
        })
        recipient.reset()
        logs_return = copy.deepcopy(self.logs)
        self._reset()
        return logs_return, chat_history

    def _check_final_result(
            self,
            messages: Optional[List[Dict]] = None,
            sender: Optional[autogen.Agent] = None,
            config: Optional[Any] = None):
        messages = messages[-1]

        if isinstance(messages, dict):
            messages = messages.get("content")
            if messages is None:
                return False, None

        cb = extract_code(messages)
        contain_code = False
        for c in cb:
            if c[0] == "python" or c[0] == "wolfram":
                contain_code = True
                break

        if (
                not contain_code
                and get_answer(messages) is not None
                and get_answer(messages) != ""
        ):
            answer = get_answer(messages)
            if not isinstance(answer, str):
                answer = str(answer)
            if "." in answer:
                try:
                    answer = str(float(answer))
                except Exception:
                    answer = str(answer)
            if answer.endswith('.0'):
                answer = answer[:-2]
            if "/" in answer:
                answer = answer.split('/')
                try:
                    answer = str(int(answer[0]) / int(answer[1]))
                    answer = str(float(answer))
                    if answer.endswith('.0'):
                        answer = answer[:-2]
                except Exception:
                    answer = str(get_answer(messages))
            answer = answer.replace(',', '')
            answer = answer.replace('"', '')
            if "frac" in answer:
                answer = answer.replace("}{", "/")
                answer = answer.replace("\\frac", "")
                answer = answer.replace("{", "")
                answer = answer.replace("}", "")
                answer = answer.split('/')
                try:
                    answer = str(int(answer[0]) / int(answer[1]))
                except Exception:
                    pass
            if answer == self._answer:
                self.logs["is_correct"] = 1
                print('Correct Answer. (This message is unseen by the assistant)')
                return True, "I've got the answer. You can let someone else to check it again with tool or code, or let someone else to reply me with the TERMINATE to end the conversation."
            else:
                self.logs["is_correct"] = 0
                print(f'Wrong Answer, correct answer is {self._answer}. (This message is unseen by the assistant)')
                return True, "I've got the answer. You can let someone else to check it again with tool or code, or let someone else to reply me with the TERMINATE to end the conversation."
        else:
            return False, None

    def _reset(self):
        self._valid_q_count = 0
        self._total_q_count = 0
        self._accum_invalid_q_per_step = 0
        self._previous_code = ""
        self.last_reply = None

        self.query = None
        self.answer = None
        self.logs = {}
        self.max_function_call_trial = 3

    def clear_function_statistic(self):
        self.function_statistic = None