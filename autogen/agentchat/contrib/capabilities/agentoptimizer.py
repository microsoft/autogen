from autogen.agentchat.assistant_agent import ConversableAgent
from autogen.code_utils import execute_code
from openai import AzureOpenAI
from typing import Optional, Union
import json
import os 

ADD_FUNC = {
    "type": "function",
    "function": {
        "name": "add_function",
        "description": "Add a function in the context of the conversation. Necessary Python packages must be declared. The name of the function MUST be the same with the function name in the code you generated.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the function in the code implementation."
                },
                "description": {
                    "type": "string",
                    "description": "A short description of the function."
                },
                "arguments": {
                    "type": "string",
                    "description": "JSON schema of arguments encoded as a string. Please note that the JSON schema only supports specific types including string, integer, object, array, boolean. (do not have float type) For example: { \"url\": { \"type\": \"string\", \"description\": \"The URL\", }}. Please avoid the error 'array schema missing items' when using array type."
                },
                "packages": {
                    "type": "string",
                    "description": "A list of package names imported by the function, and that need to be installed with pip prior to invoking the function. This solves ModuleNotFoundError. It should be string, not list."
                },
                "code": {
                    "type": "string",
                    "description": "The implementation in Python. Do not include the function declaration."
                }
            },
            "required": ["name", "description", "arguments", "packages", "code"]
        }
    }
}

REVISE_FUNC = {
    "type": "function",
    "function": {
        "name": "revise_function",
        "description": "Revise a function in the context of the conversation. Necessary Python packages must be declared. The name of the function MUST be the same with the function name in the code you generated.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the function in the code implementation."
                },
                "description": {
                    "type": "string",
                    "description": "A short description of the function."
                },
                "arguments": {
                    "type": "string",
                    "description": "JSON schema of arguments encoded as a string. Please note that the JSON schema only supports specific types including string, integer, object, array, boolean. (do not have float type) For example: { \"url\": { \"type\": \"string\", \"description\": \"The URL\", }}. Please avoid the error 'array schema missing items' when using array type."
                },
                "packages": {
                    "type": "string",
                    "description": "A list of package names imported by the function, and that need to be installed with pip prior to invoking the function. This solves ModuleNotFoundError. It should be string, not list."
                },
                "code": {
                    "type": "string",
                    "description": "The implementation in Python. Do not include the function declaration."
                }
            },
            "required": ["name", "description", "arguments", "packages", "code"]
        }
    }
}

REMOVE_FUNC = {
    "type": "function",
    "function": {
        "name": "remove_function",
        "description": "Remove one function in the context of the conversation. Once remove one function, the assistant will not use this function in future conversation.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the function in the code implementation."
                }
            },
            "required": ["name"]
        }
    }
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
List A: {current_signitures}. 
The following list are the function signatures that you have after taking {actions_num} actions to manupulate List A:
List B: {incumbent_signitures}. 

{accumerated_experience}

Here are {conversations_num} conversation histories of solving {conversations_num} tasks using List B.
History:
{conversations_history}

{statistic_informations}

According to the information I provide, please take one of four actions to manipulate list B using the functions you know. 
Instead of returning TERMINATE directly or taking no action, you should try your best to optimize the function list. Only take no action if you really think the current list is optimal, as more actions will harm performance in future tasks. 
Even adding a general function that can substitute the assistant’s repeated suggestions of Python code with the same functionality could also be helpful.
"""


class AgentOptimizer:
    """
    Base class for optimizing AutoGen agents. Specifically, it is used to optimize the function list of the userproxy-assistant agents pair.
    More information could be found in the following paper: https://arxiv.org/abs/2402.11359
    """

    def __init__(self, max_actions_per_step: int, azure_config: dict):
        """
        (These APIs are experimental and may change in the future.)
        Args: 
            max_actions_per_step (int): the maximum number of actions that the optimizer can take in one step.
            azure_config (dict): the configuration of Azure OpenAI API. It has the following filds:
                - "AZURE_OPENAI_API_KEY" (str): the API key of Azure OpenAI.
                - "api_version" (str): the version of the API.
                - "azure_endpoint" (str): the endpoint of Azure OpenAI.
                - "model" (str): the model of Azure OpenAI, and we suggest using "gpt-4-1106-preview".
        """
        self.max_actions_per_step = max_actions_per_step
        self._max_trials = 3

        self.registered_assistant = None
        self.registered_user_proxy = None
        self._conversations_history = []
        self._conversations_performance = []
        self._experience = []

        self._pre_signatures = None
        self._cur_signatures = None
        
        self.model = azure_config["model"]
        self._oai_config = azure_config
        os.environ["AZURE_OPENAI_API_KEY"] = azure_config["AZURE_OPENAI_API_KEY"] 
        self._client = AzureOpenAI(
            api_version=azure_config["api_version"],
            azure_endpoint=azure_config["azure_endpoint"],
        )

    def register_agent(self, assistant: ConversableAgent, user_proxy: ConversableAgent):
        """
        register one UserProxy-assistant agents pair that shall be trained.
        """
        self.registered_assistant = assistant
        self.registered_user_proxy = user_proxy

    def record_one_conversation(self, is_satisfied: bool): 
        """
        record one conversation history. 
        Args:
            is_satisfied: bool, whether the user is satisfied with the solution.
        """
        conversation_key = list(self.registered_assistant.chat_messages.keys())[0]
        single_history = self.registered_assistant.chat_messages[conversation_key]
        self._conversations_history.append({"Conversation {}".format(len(self._conversations_history)): single_history})
        self._conversations_performance.append({"Conversation {}".format(len(self._conversations_history)): 1 if is_satisfied else 0})

    def step(self):
        """
        one step of training.
        """
        if self._cur_signatures == None:
            current_signitures = []
        else:
            current_signitures = self._cur_signatures

        incumbent_signitures = current_signitures

        failure_experience_prompt, performance_prompt = self._construct_intermediate_prompt()

        for action_index in range(self.max_actions_per_step):
            prompt = OPT_PROMPT.format(
                conversations_history=self._conversations_history,
                conversations_num=len(self._conversations_history),
                actions_num=action_index,
                current_signitures=current_signitures,
                incumbent_signitures=incumbent_signitures,
                accumerated_experience=failure_experience_prompt,
                statistic_informations=performance_prompt,
            )
            messages = [{"role": "user", "content": prompt}]
            for _ in range(self._max_trials):
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=[ADD_FUNC, REVISE_FUNC, REMOVE_FUNC],
                    tool_choice="auto"
                )
                actions = response.choices[0].message.tool_calls
                if self._val_actions(actions, incumbent_signitures):
                    break
            if actions is not None and self._val_actions(actions, incumbent_signitures):
                incumbent_signitures = self._update_function_call(incumbent_signitures, actions)
        self._pre_signatures = self._cur_signatures
        self._cur_signatures = incumbent_signitures

    def withdraw_step(self):
        """
        withdraw previous optimization step.
        """
        self._cur_signatures = self._pre_signatures
        self._pre_signatures = None
        
        for name in list(self.registered_user_proxy._function_map.keys()):
            del self.registered_user_proxy._function_map[name]
        if "functions" in self.registered_assistant.llm_config.keys():
            for func in self.registered_assistant.llm_config["functions"]:
                self.registered_assistant.update_function_signature(func["name"], is_remove=True)
        if self._cur_signatures != None and len(self._cur_signatures) != 0:
            incumbent_signitures = []
            for action in self._cur_signatures:
                action = {
                    "action_name": "add_function",
                    "name": action.get("name"),
                    "description": action.get("description"),
                    "arguments": action.get("arguments"),
                    "packages": action.get("packages"),
                    "code": action.get("code"),
                }
                incumbent_signitures = self.update_function_call(action, incumbent_signitures, action)
                
        self._conversations_history.pop()
        self._conversations_performance.pop()

    def reset_optimizer(self):
        """
        reset the optimizer.
        """

        self.registered_assistant = None
        self.registered_user_proxy = None
        self._conversations_history = []
        self._conversations_performance = []
        self._experience = []

        self._pre_signatures = None
        self._cur_signatures = None
        

    def add_experience(self, functions: str, performance: Union[int, float]): 
        """
        inject evaluated functions-performance pair into the optimizer as experience.
        Args:
            functions (str): the function signature.
            performance (Union[int, float]): the performance of the function.
        """
        self._experience.append({"functions": functions, "performance": performance})
        self._experience = sorted(self._experience, key=lambda x: x["performance"])

    def _update_function_call(self, incumbent_signitures, actions):
        """
        update function call.
        """
        def execute_func(name, packages, code, args):
            if "," in packages:
                packages = packages.replace(",", "\", \"")
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
result={name}(args)
if result is not None: print(result)
"""
            print(f"execute_code:\n{str}")
            result = execute_code(str, use_docker=False, timeout=10)
            if result[0] != 0:
                raise Exception("Error in executing function:" + result[1])
            print(f"Result: {result[1]}")
            return result[1]

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
            name, description, arguments, packages, code, action_name = action.get("name"), action.get(
                "description"), action.get("arguments"), action.get("packages"), action.get("code"), action.get("action_name")
            if name in self.registered_user_proxy._function_map.keys():
                del self.registered_user_proxy._function_map[name]
            if action_name != "remove_function":
                function_config = {
                    "name": name,
                    "description": description,
                    "parameters": {"type": "object", "properties": arguments},
                }
                self.registered_user_proxy.register_function(
                    function_map={name: lambda **args: execute_func(name, packages, code, **args)})
                self.registered_assistant.update_function_signature(function_config, is_remove=False)

                incumbent_signitures = [item for item in incumbent_signitures if item["name"] != name]
                incumbent_signitures.append({"name": name,
                                            "description": description,
                                             "arguments": arguments,
                                             "packages": packages,
                                             "code": code})
            else:
                self.registered_assistant.update_function_signature(name, is_remove=True)
                incumbent_signitures = [item for item in incumbent_signitures if item["name"] != name]

        return incumbent_signitures

    def _construct_intermediate_prompt(self):
        """
        construct intermediate prompts.
        """
        if len(self._experience) != 0:
            failure_experience_prompt = "We also provide more examples for different functions and their corresponding performance (0-100).\n The following function signatures are arranged in are arranged in ascending order based on their performance, where higher performance indicate better quality."
            failure_experience_prompt += "\n\n"
            for item in self.historical_fails:
                failure_experience_prompt += "Function: \n" + str(item["functions"]) + "\n"
                failure_experience_prompt += "Performance: \n" + str(item["performance"]) + "\n"
            failure_experience_prompt += "\n\n"
        else:
            failure_experience_prompt = '\n\n'

        if len(self._conversations_performance) != 0:
            performance_prompt = "The following table shows the statistical information for solving each task in each conversation and indicates, whether the result is satisfied by the users. 1 represents satisfied. 0 represents not satisfied."
            performance_prompt += "\n\n"
            for item in self._conversations_performance:
                performance_prompt += str(item) + "\n"
            performance_prompt += "\n\n"
        else:
            performance_prompt = '\n\n'
            
        return failure_experience_prompt, performance_prompt

    def _val_actions(self, actions, incumbent_signitures):
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
                    if 'arguments' in function_args.keys():
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
                        compile(code, '<string>', 'exec')
                        print("successfully compiled")
                    except Exception as e:
                        print("Syntax is invalid:", e)
                        return False
            for action in actions:
                action_name = action.function.name
                if action_name == "remove_function":
                    function_args = json.loads(action.function.arguments.strip('"'))
                    if function_args.get("name") not in [item["name"] for item in incumbent_signitures]:
                        print("The function you want to remove does not exist.")
                        return False
        return True
