import json

import autogen
from autogen import Agent
from autogen.code_utils import extract_code

from utils.code_utils import extract_code_result, utils_2_prompt
from raworkflow.raworkflow import RAWorkflow
from raworkflow.raworkflow_helper import print_messages


class HumanInLoopPlannerExecutor(RAWorkflow):
    PLANNER_SYSTEM_MESSAGE = """
You are a helpful AI assistant.
You suggest coding and reasoning steps for a python coder to accomplish a task.
Do not suggest concrete code until coder explictly asks to execute a plan.
For any action beyond writing code or reasoning, convert it to a step which can be implemented by writing code.
For example, the action of browsing the web can be implemented by writing code which reads and prints the content of a web page.
Your plans should consider saving intermediate progress to disk.

When the coder explictly asks you to execute your plan, suggest code that follows the plan.

"""

    def define_agents(self):
        """
        Args:
            messages (List[Dict]): previous list of messages in the chat to resume from
            llm_config (Dict): config for the language model
        """
        # define user proxy agent in ALWAYS mode
        self.user_proxy = autogen.UserProxyAgent(
            name="user_proxy",
            human_input_mode="ALWAYS",
            code_execution_config=None,
            max_consecutive_auto_reply=10,
        )

        self.user_proxy.register_reply(
            [Agent, None],
            reply_func=print_messages,
            config={"callback": self.agent_on_receive},
        )

        prompt_suffix = utils_2_prompt(self.utils_dir)
        # define planning agent
        self.planner = autogen.AssistantAgent(
            name="planner",
            system_message=self.PLANNER_SYSTEM_MESSAGE + prompt_suffix,
            llm_config=self.llm_config,
        )
        # register a custom auto reply function
        self.planner.register_reply(
            trigger=self.user_proxy,
            reply_func=self.planner_reply_func,
            config={
                "work_dir": self.work_dir,
                "utils_dir": self.utils_dir,
            },
        )

        self.planner.register_reply(
            [Agent, None],
            reply_func=print_messages,
            config={"callback": self.agent_on_receive},
        )

    def _populate_chat_history(self, history_messages):
        """
        Populate the chat history of the agents with the messages from the history.
        """
        for msg in history_messages:
            if msg["role"] == "user":
                self.user_proxy.send(
                    msg["content"],
                    self.planner,
                    request_reply=False,
                    silent=self.silent,
                )
            elif msg["role"] == "assistant":
                self.planner.send(
                    msg["content"],
                    self.user_proxy,
                    request_reply=False,
                    silent=self.silent,
                )

    def generate_response(self, message, history_messages):
        self._populate_chat_history(history_messages)
        self.user_proxy.send(
            message,
            self.planner,
            request_reply=True,
            silent=self.silent,
        )
        reply = json.loads(self.user_proxy.last_message()["content"])
        return reply["content"], reply["code"]

    def solve_programming_task(self, task):
        # define auxilary user proxy agent (NEVER mode) and coding agent
        user_proxy = autogen.UserProxyAgent(
            name="user_proxy",
            human_input_mode="NEVER",
            code_execution_config={
                "work_dir": self.work_dir,
                "use_docker": False,
            },
            max_consecutive_auto_reply=5,
        )

        user_proxy.register_reply(
            [Agent, None],
            reply_func=print_messages,
            config={"callback": self.agent_on_receive},
        )

        prompt_suffix = utils_2_prompt(self.utils_dir)

        coding_system_message = autogen.AssistantAgent.DEFAULT_SYSTEM_MESSAGE + prompt_suffix

        # define a coding
        coder = autogen.AssistantAgent(
            name="coder",
            system_message=coding_system_message,
            llm_config=self.llm_config,
        )
        coder.register_reply(
            [Agent, None],
            reply_func=print_messages,
            config={"callback": self.agent_on_receive},
        )

        coder.initiate_chat(user_proxy, message=task, silent=self.silent)

        # scan through the conversation history and extract the final code and results
        messages = coder.chat_messages[user_proxy]
        exec_result = extract_code_result(messages)
        return exec_result

    def planner_reply_func(self, recipient, messages, sender, config):
        _, response = recipient.generate_oai_reply(messages, sender)

        code = extract_code(response)
        lang = code[0][0] if len(code) > 0 else None

        final_code = None
        if len(code) >= 1 and lang == "python":
            final_code, response = self.solve_programming_task(response)

        response = json.dumps(
            {
                "code": final_code,
                "content": response,
            }
        )

        return True, response
