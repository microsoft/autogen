import copy
import json
from typing import Dict, List, Literal, Optional, Union

import autogen
from autogen.code_utils import execute_code

ADD_FUNC = {
    "type": "function",
    "function": {
        "name": "add_function",
        "description": "Add a function in the context of the conversation. Necessary Python packages must be declared. The name of the function MUST be the same with the function name in the code you generated.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The name of the function in the code implementation."},
                "description": {"type": "string", "description": "A short description of the function."},
                "arguments": {
                    "type": "string",
                    "description": 'JSON schema of arguments encoded as a string. Please note that the JSON schema only supports specific types including string, integer, object, array, boolean. (do not have float type) For example: { "url": { "type": "string", "description": "The URL", }}. Please avoid the error \'array schema missing items\' when using array type.',
                },
                "packages": {
                    "type": "string",
                    "description": "A list of package names imported by the function, and that need to be installed with pip prior to invoking the function. This solves ModuleNotFoundError. It should be string, not list.",
                },
                "code": {
                    "type": "string",
                    "description": "The implementation in Python. Do not include the function declaration.",
                },
            },
            "required": ["name", "description", "arguments", "packages", "code"],
        },
    },
}

REVISE_FUNC = {
    "type": "function",
    "function": {
        "name": "revise_function",
        "description": "Revise a function in the context of the conversation. Necessary Python packages must be declared. The name of the function MUST be the same with the function name in the code you generated.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The name of the function in the code implementation."},
                "description": {"type": "string", "description": "A short description of the function."},
                "arguments": {
                    "type": "string",
                    "description": 'JSON schema of arguments encoded as a string. Please note that the JSON schema only supports specific types including string, integer, object, array, boolean. (do not have float type) For example: { "url": { "type": "string", "description": "The URL", }}. Please avoid the error \'array schema missing items\' when using array type.',
                },
                "packages": {
                    "type": "string",
                    "description": "A list of package names imported by the function, and that need to be installed with pip prior to invoking the function. This solves ModuleNotFoundError. It should be string, not list.",
                },
                "code": {
                    "type": "string",
                    "description": "The implementation in Python. Do not include the function declaration.",
                },
            },
            "required": ["name", "description", "arguments", "packages", "code"],
        },
    },
}

REMOVE_FUNC = {
    "type": "function",
    "function": {
        "name": "remove_function",
        "description": "Remove one function in the context of the conversation. Once remove one function, the assistant will not use this function in future conversation.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The name of the function in the code implementation."}
            },
            "required": ["name"],
        },
    },
}

OPT_PROMPT = """You are a function optimizer. Your task is to maintain a list of functions for the assistant according to the existing function list and conversation history that happens between the assistant and the user.
You can perform one of the following four actions to manipulate the function list using the functions you have:
1. Revise one existing function (using revise_function).
2. Remove one existing function (using remove_function).
3. Add one new function (using add_function).
4. Directly return "TERMINATE" to me if no more actions are needed for the current function list.

Below are the principles that you need to follow for taking these four actions.
(1) Revise one existing function:
1. Pay more attention to the failed tasks and corresponding error information, and optimize the function used in these tasks according to the conversation history if needed.
2. A failed function call can occur due to incorrect input arguments (missing arguments) or an incorrect function code implementation. You should focus more on the function code implementation and make it easy to get success function call.
3. Do not revise the function that you think works well and plays a critical role in solving the problems according to the conversation history. Only making revisions if needed.
4. Sometimes, a NameError may occur. To fix this error, you can either revise the name of the function in the code implementation or revise the name of the function call to make these two names consistent.
(2) Remove one existing function:
1. Only remove the function that you think is not needed anymore in future tasks.
(3) Add one new function:
1. The added function should be general enough to be used in future tasks. For instance, if you encounter a problem that this function can solve, or one step of it, you can use the generated function directly instead of starting from scratch
2. The added new function should solve a higher-level question that encompasses the original query and extend the code's functionality to make it more versatile and widely applicable.
3. Replace specific strings or variable names with general variables to enhance the tool's applicability to various queries. All names used inside the function should be passed in as arguments.
Below is an example of a function that potentially deserves to be adde in solving MATH problems, which can be used to solve a higher-level question:
{{
    \"name\": \"evaluate_expression\",
    \"description\": \"Evaluate arithmetic or mathematical expressions provided as strings.\",
    \"arguments\": {{
        \"expression\": {{
            \"type\": \"string\",
            \"description\": \"The mathematical expression to evaluate.\"
        }}
    }},
    \"packages\": \"sympy\",
    \"code\": \"from sympy import sympify, SympifyError\\n\\ndef evaluate_expression(expression):\\n    try:\\n        result = sympify(expression)\\n        if result.is_number:\\n            result = float(result)\\n        else:\\n            result = str(result)\\n        return result\\n    except SympifyError as e:\\n        return str(e)\"
}}
(4) Directly return "TERMINATE":
If you think there is no need to perform any other actions for the current function list since the current list is optimal more actions will harm the performance in future tasks. Please directly reply to me with "TERMINATE".

One function signature includes the following five elements:
1. Function name
2. Function description
3. JSON schema of arguments encoded as a string
4. A list of package names imported by the function packages
5. The code implementation

Below are the signatures of the current functions:
List A: {best_functions}.
The following list are the function signatures that you have after taking {actions_num} actions to manipulate List A:
List B: {incumbent_functions}.

{accumulated_experience}

Here are {best_conversations_num} conversation histories of solving {best_conversations_num} tasks using List A.
History:
{best_conversations_history}

{statistic_informations}

According to the information I provide, please take one of four actions to manipulate list B using the functions you know.
Instead of returning TERMINATE directly or taking no action, you should try your best to optimize the function list. Only take no action if you really think the current list is optimal, as more actions will harm performance in future tasks.
Even adding a general function that can substitute the assistant’s repeated suggestions of Python code with the same functionality could also be helpful.
"""


def execute_func(name, packages, code, **args):
    """
    The wrapper for generated functions.
    """
    pip_install = (
        f"""print("Installing package: {packages}")\nsubprocess.run(["pip", "-qq", "install", "{packages}"])"""
        if packages
        else ""
    )
    str = f"""
import subprocess
{pip_install}
print("Result of {name} function execution:")
{code}
args={args}
result={name}(**args)
if result is not None: print(result)
"""
    print(f"execute_code:\n{str}")
    result = execute_code(str, use_docker="shaokun529/evoagent:v1")
    if result[0] != 0:
        raise Exception("Error in executing function:" + result[1])
    print(f"Result: {result[1]}")
    return result[1]


class AgentOptimizer:
    """
    Base class for optimizing AutoGen agents. Specifically, it is used to optimize the functions used in the agent.
    More information could be found in the following paper: https://arxiv.org/abs/2402.11359.
    """

    def __init__(
        self,
        max_actions_per_step: int,
        llm_config: dict,
        optimizer_model: Optional[str] = "gpt-4-1106-preview",
    ):
        """
        (These APIs are experimental and may change in the future.)
        Args:
            max_actions_per_step (int): the maximum number of actions that the optimizer can take in one step.
            llm_config (dict): llm inference configuration.
                Please refer to [OpenAIWrapper.create](/docs/reference/oai/client#create) for available options.
                When using OpenAI or Azure OpenAI endpoints, please specify a non-empty 'model' either in `llm_config` or in each config of 'config_list' in `llm_config`.
            optimizer_model: the model used for the optimizer.
        """
        self.max_actions_per_step = max_actions_per_step
        self._max_trials = 3
        self.optimizer_model = optimizer_model

        self._trial_conversations_history = []
        self._trial_conversations_performance = []
        self._trial_functions = []

        self._best_conversations_history = []
        self._best_conversations_performance = []
        self._best_functions = []

        self._failure_functions_performance = []
        self._best_performance = -1

        assert isinstance(llm_config, dict), "llm_config must be a dict"
        llm_config = copy.deepcopy(llm_config)
        self.llm_config = llm_config
        if self.llm_config in [{}, {"config_list": []}, {"config_list": [{"model": ""}]}]:
            raise ValueError(
                "When using OpenAI or Azure OpenAI endpoints, specify a non-empty 'model' either in 'llm_config' or in each config of 'config_list'."
            )
        self.llm_config["config_list"] = autogen.filter_config(
            llm_config["config_list"], {"model": [self.optimizer_model]}
        )
        self._client = autogen.OpenAIWrapper(**self.llm_config)

    def record_one_conversation(self, conversation_history: List[Dict], is_satisfied: bool = None):
        """
        record one conversation history.
        Args:
            conversation_history (List[Dict]): the chat messages of the conversation.
            is_satisfied (bool): whether the user is satisfied with the solution. If it is none, the user will be asked to input the satisfaction.
        """
        if is_satisfied is None:
            reply = input(
                "Please provide whether the user is satisfied with the solution. 1 represents satisfied. 0 represents not satisfied. Press enter to submit. \n"
            )
            assert reply in [
                "0",
                "1",
            ], "The input is invalid. Please input 1 or 0. 1 represents satisfied. 0 represents not satisfied."
            is_satisfied = True if reply == "1" else False
        self._trial_conversations_history.append(
            {"Conversation {i}".format(i=len(self._trial_conversations_history)): conversation_history}
        )
        self._trial_conversations_performance.append(
            {"Conversation {i}".format(i=len(self._trial_conversations_performance)): 1 if is_satisfied else 0}
        )

    def step(self):
        """
        One step of training. It will return register_for_llm and register_for_executor at each iteration,
        which are subsequently utilized to update the assistant and executor agents, respectively.
        See example: https://github.com/microsoft/autogen/blob/main/notebook/agentchat_agentoptimizer.ipynb
        """
        performance = sum(sum(d.values()) for d in self._trial_conversations_performance) / len(
            self._trial_conversations_performance
        )

        if performance < self._best_performance:
            self._failure_functions_performance.append({"functions": self._trial_functions, "performance": performance})
            self._failure_functions_performance = sorted(
                self._failure_functions_performance, key=lambda x: x["performance"]
            )
        else:
            self._failure_functions_performance = []
            self._best_performance = performance
            self._best_functions = copy.deepcopy(self._trial_functions)
            self._best_conversations_history = copy.deepcopy(self._trial_conversations_history)
            self._best_conversations_performance = copy.deepcopy(self._trial_conversations_performance)
        self._trial_conversations_history = []
        self._trial_conversations_performance = []

        best_functions = copy.deepcopy(self._best_functions)
        incumbent_functions = copy.deepcopy(self._best_functions)
        failure_experience_prompt, statistic_prompt = self._construct_intermediate_prompt()

        for action_index in range(self.max_actions_per_step):
            prompt = OPT_PROMPT.format(
                best_conversations_history=self._best_conversations_history,
                best_conversations_num=len(self._best_conversations_history),
                actions_num=action_index,
                best_functions=best_functions,
                incumbent_functions=incumbent_functions,
                accumulated_experience=failure_experience_prompt,
                statistic_informations=statistic_prompt,
            )
            messages = [{"role": "user", "content": prompt}]
            for _ in range(self._max_trials):
                response = self._client.create(
                    messages=messages, tools=[ADD_FUNC, REVISE_FUNC, REMOVE_FUNC], tool_choice="auto"
                )
                actions = response.choices[0].message.tool_calls
                if self._validate_actions(actions, incumbent_functions):
                    break
            if actions is not None and self._validate_actions(actions, incumbent_functions):
                incumbent_functions = self._update_function_call(incumbent_functions, actions)

        remove_functions = list(
            set([key for dictionary in self._trial_functions for key in dictionary.keys()])
            - set([key for dictionary in incumbent_functions for key in dictionary.keys()])
        )

        register_for_llm = []
        register_for_exector = {}
        for name in remove_functions:
            register_for_llm.append({"func_sig": {"name": name}, "is_remove": True})
            register_for_exector.update({name: None})
        for func in incumbent_functions:
            register_for_llm.append(
                {
                    "func_sig": {
                        "name": func.get("name"),
                        "description": func.get("description"),
                        "parameters": {"type": "object", "properties": func.get("arguments")},
                    },
                    "is_remove": False,
                }
            )
            register_for_exector.update(
                {
                    func.get("name"): lambda **args: execute_func(
                        func.get("name"), func.get("packages"), func.get("code"), **args
                    )
                }
            )

        self._trial_functions = incumbent_functions
        return register_for_llm, register_for_exector

    def reset_optimizer(self):
        """
        reset the optimizer.
        """

        self._trial_conversations_history = []
        self._trial_conversations_performance = []
        self._trial_functions = []

        self._best_conversations_history = []
        self._best_conversations_performance = []
        self._best_functions = []

        self._best_performance = -1
        self._failure_functions_performance = []

    def _update_function_call(self, incumbent_functions, actions):
        """
        update function call.
        """

        formated_actions = []
        for action in actions:
            func = json.loads(action.function.arguments.strip('"'))
            func["action_name"] = action.function.name

            if func.get("action_name") == "remove_function":
                item = {
                    "action_name": func.get("action_name"),
                    "name": func.get("name"),
                }
            else:
                item = {
                    "action_name": func.get("action_name"),
                    "name": func.get("name"),
                    "description": func.get("description"),
                    "arguments": json.loads(func.get("arguments").strip('"')),
                    "packages": func.get("packages"),
                    "code": func.get("code"),
                }
            formated_actions.append(item)
        actions = formated_actions

        for action in actions:
            name, description, arguments, packages, code, action_name = (
                action.get("name"),
                action.get("description"),
                action.get("arguments"),
                action.get("packages"),
                action.get("code"),
                action.get("action_name"),
            )
            if action_name == "remove_function":
                incumbent_functions = [item for item in incumbent_functions if item["name"] != name]
            else:
                incumbent_functions = [item for item in incumbent_functions if item["name"] != name]
                incumbent_functions.append(
                    {
                        "name": name,
                        "description": description,
                        "arguments": arguments,
                        "packages": packages,
                        "code": code,
                    }
                )

        return incumbent_functions

    def _construct_intermediate_prompt(self):
        """
        construct intermediate prompts.
        """
        if len(self._failure_functions_performance) != 0:
            failure_experience_prompt = "We also provide more examples for different functions and their corresponding performance (0-100).\n The following function signatures are arranged in are arranged in ascending order based on their performance, where higher performance indicate better quality."
            failure_experience_prompt += "\n"
            for item in self._failure_functions_performance:
                failure_experience_prompt += "Function: \n" + str(item["functions"]) + "\n"
                failure_experience_prompt += "Performance: \n" + str(item["performance"]) + "\n"
        else:
            failure_experience_prompt = "\n"

        if len(self._best_conversations_performance) != 0:
            statistic_prompt = "The following table shows the statistical information for solving each task in each conversation and indicates, whether the result is satisfied by the users. 1 represents satisfied. 0 represents not satisfied."
            statistic_prompt += "\n"
            for item in self._best_conversations_performance:
                statistic_prompt += str(item) + "\n"
        else:
            statistic_prompt = "\n"

        return failure_experience_prompt, statistic_prompt

    def _validate_actions(self, actions, incumbent_functions):
        """
        validate whether the proposed actions are feasible.
        """
        if actions is None:
            return True
        else:
            # val json format
            for action in actions:
                function_args = action.function.arguments
                try:
                    function_args = json.loads(function_args.strip('"'))
                    if "arguments" in function_args.keys():
                        json.loads(function_args.get("arguments").strip('"'))
                except Exception as e:
                    print("JSON is invalid:", e)
                    return False
            # val syntax
            for action in actions:
                if action.function.name != "remove_function":
                    function_args = json.loads(action.function.arguments.strip('"'))
                    code = function_args.get("code")
                    try:
                        compile(code, "<string>", "exec")
                        print("successfully compiled")
                    except Exception as e:
                        print("Syntax is invalid:", e)
                        return False
            for action in actions:
                action_name = action.function.name
                if action_name == "remove_function":
                    function_args = json.loads(action.function.arguments.strip('"'))
                    if function_args.get("name") not in [item["name"] for item in incumbent_functions]:
                        print("The function you want to remove does not exist.")
                        return False
        return True
