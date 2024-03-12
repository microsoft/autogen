import json
import re
from typing import Dict, Union, Tuple
import autogen

from typing_extensions import override

from autogen import OpenAIWrapper

""" This module contains the NexusFunctionCallingAssistant class, which is a subclass of the autogen.AssistantAgent class.
    Its used specifically for calling functions locally using <a href="https://huggingface.co/TheBloke/NexusRaven-V2-13
    The model can be imported from hugging face and the can use the standard function calling decorator to register the functions to be called.
    If you enjoyed this module consider giving me a follow on github or buying me a coffee at https://www.buymeacoffee.com/gregnwosu
    """


def create_nexus_prompt_for_tool(tool: dict) -> str:
    ''' takes a dictionary of form
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
    function = tool['function']
    name = function['name']
    description = function['description']
    parameters = function['parameters']
    properties = parameters['properties']

    args = ', '.join([f"{k}:{v['type']}" for k, v in properties.items()])
    arg_types = ',\n'.join(
        [f"{key} ({properties[key]['type']}): {properties[key]['description']}" for key in properties.keys()])
    return f'''OPTION:\n<func_start>def {name}({args})<func_end>\n<docstring_start>\n"""\n{description.strip()}\n\nArgs:\n{arg_types}\n"""\n<docstring_end>'''


def add_nexus_raven_prompts(func):
    """
      ->    messages:[{'content': ' functioncaller.random_word_generator().then(randomWord => mistral.speak(`Using the randomly generated word "${randomWord}," I will now solve this logic problem.`));',
              'name': 'mistral', 'role': 'user'}],
              'tools': [
                      {'type': 'function',
                      'function': {'description': 'terminate the group chat',
                                   'name': 'terminate_group_chat',
                                   'parameters': {'type': 'object',
                                                  'properties': {'message': {'type': 'string',
                                                                             'description': 'Message to be sent to the group chat.'}},
                                                  'required': ['message']}}},
                     {'type': 'function',
                     'function': {'description': 'This is a random word generator.',
                                  'name': 'random_word_generator',
                                  'parameters': {'type': 'object',
                                                 'properties': {'seed':   {'type': 'integer',
                                                                           'description': 'seed for initialising the random generator'},
                                                                'prefix': {'type': 'string',
                                                                           'description': 'string to prefix random word'}},
                                                 'required': ['seed', 'prefix']}}}],
             'model': 'nexusraven'}]"""
    if getattr(func, '_is_decorated', False):
        # If the function is already decorated, return it as is
        return func

    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)

        # extract the tools element from the result
        query_header = "\n\n".join(
            [create_nexus_prompt_for_tool(tool) for tool in result['tools'] if tool['type'] == 'function'])

        query = "\n".join([m['content'] for m in result['messages'][-1:]])
        prompt = f"""<human>:\n{query_header}\nUser Query: Question: {query} \n suggest a function and suitable argument values for the situation conversation:  """
        del result['messages']
        del result['tools']
        result['prompt'] = prompt

        result['extra_query'] = {"inputs": prompt,
                                 "parameters": {"temperature": 0.001, "do_sample": False, "max_new_tokens": 2000}}
        result['extra_body'] = {"prompt": prompt}
        return result

    wrapper._is_decorated = True
    return wrapper


class NexusFunctionCallingAssistant(autogen.ConversableAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.register_reply([autogen.Agent, None], NexusFunctionCallingAssistant.generate_oai_reply)

    @staticmethod
    def parse_function_details(input_string: str) -> Tuple[str, Dict[str, str], str] | None:
        call_part, thought_part = input_string.split("(<bot_end> \n)?Thought: ")
        function_name_match = re.search(r'Call: (\w+)', call_part)
        function_name = function_name_match.group(1) if function_name_match else None
        args_match = re.search(r'\((.*?)\)', call_part)
        args_str = args_match.group(1) if args_match else ''
        args_list = args_str.split(', ')
        args_map = {}
        for arg in args_list:
            key, value = arg.split('=')
            args_map[key.strip()] = value.strip().strip('\'')
        return function_name, args_map, thought_part.strip()

    @override
    def _generate_oai_reply_from_client(self, llm_client: OpenAIWrapper, messages: list[dict], cache:) -> Union[str, Dict, None]:
        llm_client._construct_create_params = add_nexus_raven_prompts(llm_client._construct_create_params)
        all_messages = []
        for message in messages:
            tool_responses = message.get("tool_responses", [])
            if tool_responses:
                all_messages += tool_responses
                # tool role on the parent message means the content is just concatenation of all of the tool_responses
                if message.get("role") != "tool":
                    all_messages.append({key: message[key] for key in message if key != "tool_responses"})
            else:
                all_messages.append(message)

        response = llm_client.create(
            context=messages[-1].pop("context", dict()),
            messages=all_messages,
            cache=cache,
        )
        function_name, args_map, thought_part = NexusFunctionCallingAssistant.parse_function_details(
            response.choices[0].model_extra['message']['content'])
        return {'content': thought_part,
                'function_call': None,
                'role': 'assistant',
                'tool_calls': [
                    {'id': response.id,
                     'function':
                         {'arguments': json.dumps(args_map), #TODO this json dumps is causing all args values to be wrapped in quotes
                          'name': function_name},
                     'type': 'function'}
                ]
                }
