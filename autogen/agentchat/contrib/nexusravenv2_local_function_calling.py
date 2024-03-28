import json
import re
import warnings
from typing import Dict, Union, Tuple, Optional

from typing_extensions import override

import autogen
from autogen import OpenAIWrapper, Agent
from autogen.code_utils import content_str

""" This module contains the NexusFunctionCallingAssistant class, which is a subclass of the autogen.AssistantAgent class.
    Its used specifically for calling functions locally using <a href="https://huggingface.co/TheBloke/NexusRaven-V2-13
    The model can be imported from hugging face and the can use the standard function calling decorator to register the functions to be called.
    If you enjoyed this module consider giving me a follow on github or buying me a coffee at https://www.buymeacoffee.com/gregnwosu
    """


# TODO this does not include return type
def create_nexus_prompt_for_tool(tool: dict) -> str:
    '''takes a dictionary of form
        {'type': 'function',
         'function': {'description': 'This is a random word generator.',
                      'name': 'random_word_generator',
                      'parameters': {'type': 'object',
                                     'properties': {'seed':   {'type': 'integer',
                                                                'description': 'seed for initialising the random generator'},
                                                     'prefix': {'type': 'string',
                                                                'description': 'string to prefix random word'}},
                                      'required': ['seed', 'prefix']}}}
        and produces a string of the form:

        Function:
        def random_word_generator(seed, pre):
            """
            This is a random word generator.

            Args:
            seed (integer): seed for initialising the random generator.
            prefix (string): string to prefix random word.

            Returns:
            float: a random word
    """
    '''
    function_data = tool["function"]
    name = function_data["name"]
    description = function_data["description"]
    parameters = function_data["parameters"]
    properties = parameters["properties"]

    def type_to_str(data_type: str) -> str:
        if data_type == "integer":
            return "int"
        if data_type == "string":
            return "str"
        if data_type == "number":
            return "float"
        return data_type

    args = ", ".join([f"{k}: {type_to_str(v['type'])}" for k, v in properties.items()])
    arg_types = "\n".join(
        [
            f"{key} ({type_to_str(properties[key]['type'])}): {properties[key]['description']}"
            for key in properties.keys()
        ]
    )
    docstring = f'"""\n{description.strip()}\n\nArgs:\n{arg_types}\n"""'
    # Indent the docstring
    docstring = "\n".join(["    " + line for line in docstring.split("\n")])

    return f"""Function:\ndef {name}({args}):\n{docstring}"""


class NexusFunctionCallingAssistant(autogen.ConversableAgent):
    def __init__(
            self,
            llm_config,
            name="nexusraven2functioncaller",
            system_message="""Function calling assistant""",
            description="""a function call advisor. given a context advises on what functions to call and what arguments to supply.
                                   translates the standard nexusravenv2 responses
                                   from:
                                      Call: function_name(arg1=value1, arg2=value2) <bot_end> Thought: some thought
                                   to:
                                   { "function_call": {"name": "function_name", "arguments": {"arg1": "value1", "arg2": "value2"}}}""",
    ):
        for config in llm_config["config_list"]:
            config["temperature"] = 0.001

        super().__init__(
            llm_config=llm_config,
            name=name,
            system_message=system_message,
            code_execution_config=False,
            description=description,
        )

    @staticmethod
    def parse_function_details(input_string: str) -> Union[Tuple[str, Dict[str, str], str], None]:
        result = re.split(r"(<bot_end> \n)?Thought: ", input_string)

        print(f"\n\n\n\n****************** {result}************** \n\n\n\n")

        call_part, thought_part = re.split(r"(?:<bot_end> \n)?Thought: ", input_string)

        function_name_match = re.search(r"Call: (\w+)", call_part)
        function_name = function_name_match.group(1) if function_name_match else None
        args_match = re.search(r"\((.*?)\)", call_part)
        args_str = args_match.group(1) if args_match else ""
        args_list = args_str.split(", ")
        args_map = {}
        for arg in args_list:
            key, value = arg.split("=")
            args_map[key.strip()] = (
                value.strip().strip("'") if "'" in value else float(value) if "." in value else int(value)
            )

        return function_name, args_map, thought_part.strip()

    @override
    def receive(
            self,
            message: Union,
            sender: Agent,
            request_reply: Optional = None,
            silent: Optional = False,
    ):
        self._process_received_message(message, sender, silent)
        if request_reply is False or request_reply is None and self.reply_at_receive[sender] is False:
            return
        reply = self.generate_reply(messages=self.chat_messages[sender], sender=sender)
        function_name, args_map, thought_part = NexusFunctionCallingAssistant.parse_function_details(reply)
        formatted_reply = {
            "content": thought_part,
            "function_call": None,
            "role": "assistant",
            "tool_calls": [
                {
                    "id": 43,  # TODO fix this as response id , was generate_oai_reply
                    "function": {"arguments": json.dumps(args_map), "name": function_name},
                    "type": "function",
                }
            ],
        }
        if formatted_reply is not None:
            self.send(formatted_reply, sender, silent=silent)

    @override
    def _generate_oai_reply_from_client(
            self, llm_client: OpenAIWrapper, messages: list, cache: autogen.Cache
    ) -> Union[str, Dict, None]:
        # We make a big assumption here that the last message is the user query.
        query = content_str(messages[-1]["content"])

        tools = self.llm_config["tools"]
        functions = "\n\n".join([create_nexus_prompt_for_tool(tool) for tool in tools if tool["type"] == "function"])
        prompt = f"""{functions}\n\nUser Query: {query}<human_end>"""
        all_messages = [{"content": prompt, "role": "user"}]

        response = llm_client.create(
            context=None,
            messages=all_messages,
            cache=cache,
        )

        extracted_response = llm_client.extract_text_or_completion_object(response)[0]

        if extracted_response is None:
            warnings.warn("Extracted_response from {response} is None.", UserWarning)
            return None

        if not isinstance(extracted_response, str):
            raise ValueError(f"Expected extracted_response to be a string, but got {extracted_response}")

        # TODO - handle if the produced call is nested.
        function_name, args_map, thought_part = NexusFunctionCallingAssistant.parse_function_details(extracted_response)
        return {
            "content": thought_part,
            "function_call": None,
            "role": "assistant",
            "tool_calls": [
                {
                    "id": response.id,
                    "function": {"arguments": json.dumps(args_map), "name": function_name},
                    "type": "function",
                }
            ],
        }


def test_parse_function_details():
    input_string = "Call: random_word_generator(seed=42, prefix='chase')<bot_end> \nThought: functioncaller.random_word_generator().then(randomWord => mistral.speak(`Using the randomly generated word \"${randomWord},\" I will now solve this logic problem.`));"
    assert NexusFunctionCallingAssistant.parse_function_details(input_string) == (
        "random_word_generator",
        {"seed": 42, "prefix": "chase"},
        'functioncaller.random_word_generator().then(randomWord => mistral.speak(`Using the randomly generated word "${randomWord}," I will now solve this logic problem.`));',
    )
