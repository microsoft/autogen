"""Create a OpenAI-compatible client for Gemini features.


Example:
    llm_config={
        "config_list": [{
            "api_type": "google",
            "model": "gemini-pro",
            "api_key": os.environ.get("GOOGLE_API_KEY"),
            "safety_settings": [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
                    ],
            "top_p":0.5,
            "max_tokens": 2048,
            "temperature": 1.0,
            "top_k": 5
            }
    ]}

    agent = autogen.AssistantAgent("my_agent", llm_config=llm_config)

Resources:
- https://ai.google.dev/docs
- https://cloud.google.com/vertex-ai/docs/generative-ai/migrate-from-azure
- https://blog.google/technology/ai/google-gemini-pro-imagen-duet-ai-update/
- https://ai.google.dev/api/python/google/generativeai/ChatSession
"""

from __future__ import annotations

import base64
import copy
import json
import os
import random
import re
import time
import warnings
from io import BytesIO
from typing import Any, Dict, List

import google.generativeai as genai
import requests
from google.ai.generativelanguage import Content, FunctionCall, FunctionDeclaration, FunctionResponse, Part, Tool
import vertexai
from google.api_core.exceptions import InternalServerError
from openai.types.chat import ChatCompletion, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion import ChatCompletionMessage, Choice
from openai.types.chat.chat_completion_message_tool_call import Function
from openai.types.completion_usage import CompletionUsage
from PIL import Image
from vertexai.generative_models import Content as VertexAIContent, FunctionDeclaration as VertexAIFunctionDeclaration, Tool as VertexAITool
from vertexai.generative_models import GenerativeModel
from vertexai.generative_models import Part as VertexAIPart


class GeminiClient:
    """Client for Google's Gemini API.

    Please visit this [page](https://github.com/microsoft/autogen/issues/2387) for the roadmap of Gemini integration
    of AutoGen.
    """

    # Mapping, where Key is a term used by Autogen, and Value is a term used by Gemini
    PARAMS_MAPPING = {
        "max_tokens": "max_output_tokens",
        # "n": "candidate_count", # Gemini supports only `n=1`
        "stop_sequences": "stop_sequences",
        "temperature": "temperature",
        "top_p": "top_p",
        "top_k": "top_k",
        "max_output_tokens": "max_output_tokens",
    }

    def _initialize_vartexai(self, **params):
        if "google_application_credentials" in params:
            # Path to JSON Keyfile
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = params["google_application_credentials"]
        vertexai_init_args = {}
        if "project_id" in params:
            vertexai_init_args["project"] = params["project_id"]
        if "location" in params:
            vertexai_init_args["location"] = params["location"]
        if vertexai_init_args:
            vertexai.init(**vertexai_init_args)

    def __init__(self, **kwargs):
        """Uses either either api_key for authentication from the LLM config
        (specifying the GOOGLE_API_KEY environment variable also works),
        or follows the Google authentication mechanism for VertexAI in Google Cloud if no api_key is specified,
        where project_id and location can also be passed as parameters. Service account key file can also be used.
        If neither a service account key file, nor the api_key are passed, then the default credentials will be used,
        which could be a personal account if the user is already authenticated in, like in Google Cloud Shell.

        Args:
            api_key (str): The API key for using Gemini.
            google_application_credentials (str): Path to the JSON service account key file of the service account.
            Alternatively, the GOOGLE_APPLICATION_CREDENTIALS environment variable
            can also be set instead of using this argument.
            project_id (str): Google Cloud project id, which is only valid in case no API key is specified.
            location (str): Compute region to be used, like 'us-west1'.
            This parameter is only valid in case no API key is specified.
        """
        self.api_key = kwargs.get("api_key", None)
        if not self.api_key:
            self.api_key = os.getenv("GOOGLE_API_KEY")
            if self.api_key is None:
                self.use_vertexai = True
                self._initialize_vartexai(**kwargs)
            else:
                self.use_vertexai = False
        else:
            self.use_vertexai = False
        if not self.use_vertexai:
            assert ("project_id" not in kwargs) and (
                "location" not in kwargs
            ), "Google Cloud project and compute location cannot be set when using an API Key!"

    def message_retrieval(self, response) -> List:
        """
        Retrieve and return a list of strings or a list of Choice.Message from the response.

        NOTE: if a list of Choice.Message is returned, it currently needs to contain the fields of OpenAI's ChatCompletion Message object,
        since that is expected for function or tool calling in the rest of the codebase at the moment, unless a custom agent is being used.
        """
        return [choice.message for choice in response.choices]

    def cost(self, response) -> float:
        return response.cost

    @staticmethod
    def get_usage(response) -> Dict:
        """Return usage summary of the response using RESPONSE_USAGE_KEYS."""
        # ...  # pragma: no cover
        return {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "cost": response.cost,
            "model": response.model,
        }

    def create(self, params: Dict) -> ChatCompletion:
        if self.use_vertexai:
            self._initialize_vartexai(**params)
        else:
            assert ("project_id" not in params) and (
                "location" not in params
            ), "Google Cloud project and compute location cannot be set when using an API Key!"
        model_name = params.get("model", "gemini-pro")
        if not model_name:
            raise ValueError(
                "Please provide a model name for the Gemini Client. "
                "You can configurate it in the OAI Config List file. "
                "See this [LLM configuration tutorial](https://microsoft.github.io/autogen/docs/topics/llm_configuration/) for more details."
            )

        params.get("api_type", "google")  # not used
        messages = params.get("messages", [])
        tools = params.get("tools", [])
        stream = params.get("stream", False)
        n_response = params.get("n", 1)

        generation_config = {
            gemini_term: params[autogen_term]
            for autogen_term, gemini_term in self.PARAMS_MAPPING.items()
            if autogen_term in params
        }
        safety_settings = params.get("safety_settings", {})

        if stream:
            warnings.warn(
                "Streaming is not supported for Gemini yet, and it will have no effect. Please set stream=False.",
                UserWarning,
            )

        if n_response > 1:
            warnings.warn("Gemini only supports `n=1` for now. We only generate one response.", UserWarning)

        if "vision" not in model_name:
            # A. create and call the chat model.
            gemini_messages = self._oai_messages_to_gemini_messages(messages)
            gemini_tools = self._oai_tools_to_gemini_tools(tools)
            if self.use_vertexai:
                model = GenerativeModel(
                    model_name, generation_config=generation_config, safety_settings=safety_settings, tools=gemini_tools
                )
            else:
                # we use chat model by default
                model = genai.GenerativeModel(
                    model_name, generation_config=generation_config, safety_settings=safety_settings, tools=gemini_tools
                )
                genai.configure(api_key=self.api_key)
            chat = model.start_chat(history=gemini_messages[:-1])
            max_retries = 5
            for attempt in range(max_retries):
                ans: Content = None
                try:
                    response = chat.send_message(gemini_messages[-1].parts, stream=stream)
                except InternalServerError:
                    delay = 5 * (2**attempt)
                    warnings.warn(
                        f"InternalServerError `500` occurs when calling Gemini's chat model. Retry in {delay} seconds...",
                        UserWarning,
                    )
                    time.sleep(delay)
                except Exception as e:
                    raise RuntimeError(f"Google GenAI exception occurred while calling Gemini API: {e}")
                else:
                    # `ans = response.text` is unstable. Use the following code instead.
                    ans: Content = chat.history[-1]
                    break

            if ans is None:
                raise RuntimeError(f"Fail to get response from Google AI after retrying {attempt + 1} times.")

            prompt_tokens = model.count_tokens(chat.history[:-1]).total_tokens
            if self.use_vertexai:
                completion_tokens = model.count_tokens(contents=VertexAIContent(parts=ans.parts)).total_tokens
            else:
                completion_tokens = model.count_tokens(contents=Content(parts=ans.parts)).total_tokens
        elif model_name == "gemini-pro-vision":
            # B. handle the vision model
            if self.use_vertexai:
                model = GenerativeModel(
                    model_name, generation_config=generation_config, safety_settings=safety_settings
                )
            else:
                model = genai.GenerativeModel(
                    model_name, generation_config=generation_config, safety_settings=safety_settings
                )
                genai.configure(api_key=self.api_key)
            # Gemini's vision model does not support chat history yet
            # chat = model.start_chat(history=gemini_messages[:-1])
            # response = chat.send_message(gemini_messages[-1])
            user_message = self._oai_content_to_gemini_content(messages[-1])
            if len(messages) > 2:
                warnings.warn(
                    "Warning: Gemini's vision model does not support chat history yet.",
                    "We only use the last message as the prompt.",
                    UserWarning,
                )

            response = model.generate_content(user_message, stream=stream)
            # ans = response.text
            if self.use_vertexai:
                ans: str = response.candidates[0].content.parts[0].text
            else:
                ans: Content = response._result.candidates[0].content

            prompt_tokens = model.count_tokens(user_message).total_tokens
            completion_tokens = model.count_tokens(ans.parts[0].text).total_tokens

        # 3. convert output
        choices = self._gemini_content_to_oai_choices(ans)

        response_oai = ChatCompletion(
            id=str(random.randint(0, 1000)),
            model=model_name,
            created=int(time.time() * 1000),
            object="chat.completion",
            choices=choices,
            usage=CompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            cost=self._calculate_gemini_cost(prompt_tokens, completion_tokens, model_name),
        )

        return response_oai
    
    # If str is not a json string return str as is
    def _to_json(self, str) -> dict:
        try:
            return json.loads(str)
        except ValueError:
            return str
    
    def _oai_content_to_gemini_content(self, message: Dict[str, Any]) -> List:
        """Convert content from OAI format to Gemini format"""
        rst = []
        if isinstance(message, str):
            if self.use_vertexai:
                rst.append(VertexAIPart.from_text(message))
            else:
                rst.append(Part(text=message))
            return rst

        if "tool_calls" in message:
            if self.use_vertexai:
                rst.append(VertexAIPart.from_dict({
                    "functionCall": {
                        "name": message["tool_calls"][0]["function"]["name"],
                        "args": json.loads(message["tool_calls"][0]["function"]["arguments"])
                    }
                }))
            else:
                rst.append(
                    Part(
                        function_call=FunctionCall(
                            name=message["tool_calls"][0]["function"]["name"],
                            args=json.loads(message["tool_calls"][0]["function"]["arguments"]),
                        )
                    )
                )
            return rst

        if message["role"] == "tool":
            if self.use_vertexai:
                rst.append(VertexAIPart.from_function_response(
                    name=message["name"],
                    response={"result": self._to_json(message["content"])}
                ))
            else:
                rst.append(
                    Part(function_response=FunctionResponse(name=message["name"], response={"result": self._to_json(message["content"])}))
                )
            return rst

        if isinstance(message["content"], str):
            if self.use_vertexai:
                rst.append(VertexAIPart.from_text(message["content"]))
            else:
                rst.append(Part(text=message["content"]))
            return rst

        assert isinstance(message["content"], list)

        for msg in message["content"]:
            if isinstance(msg, dict):
                assert "type" in msg, f"Missing 'type' field in message: {msg}"
                if msg["type"] == "text":
                    if self.use_vertexai:
                        rst.append(VertexAIPart.from_text(msg["text"]))
                    else:
                        rst.append(Part(text=msg["text"]))
                elif msg["type"] == "image_url":
                    if self.use_vertexai:
                        img_url = msg["image_url"]["url"]
                        re.match(r"data:image/(?:png|jpeg);base64,", img_url)
                        img = get_image_data(img_url, use_b64=False)
                        # image/png works with jpeg as well
                        img_part = VertexAIPart.from_data(img, mime_type="image/png")
                        rst.append(img_part)
                    else:
                        b64_img = get_image_data(msg["image_url"]["url"])
                        img = _to_pil(b64_img)
                        rst.append(img)
                else:
                    raise ValueError(f"Unsupported message type: {msg['type']}")
            else:
                raise ValueError(f"Unsupported message type: {type(msg)}")
        return rst

    def _calculate_gemini_cost(self, input_tokens: int, output_tokens: int, model_name: str) -> float:
        if "1.5-pro" in model_name:
            if (input_tokens + output_tokens) <= 128000:
                # "gemini-1.5-pro"
                # When total tokens is less than 128K cost is $3.5 per million input tokens and $10.5 per million output tokens
                return 3.5 * input_tokens / 1e6 + 10.5 * output_tokens / 1e6
            # "gemini-1.5-pro"
            # Cost is $7 per million input tokens and $21 per million output tokens
            return 7.0 * input_tokens / 1e6 + 21.0 * output_tokens / 1e6

        if "1.5-flash" in model_name:
            if (input_tokens + output_tokens) <= 128000:
                # "gemini-1.5-flash"
                # Cost is $0.35 per million input tokens and $1.05 per million output tokens
                return 0.35 * input_tokens / 1e6 + 1.05 * output_tokens / 1e6
            # "gemini-1.5-flash"
            # When total tokens is less than 128K cost is $0.70 per million input tokens and $2.10 per million output tokens
            return 0.70 * input_tokens / 1e6 + 2.10 * output_tokens / 1e6

        if "gemini-pro" not in model_name and "gemini-1.0-pro" not in model_name:
            warnings.warn(f"Cost calculation is not implemented for model {model_name}. Using Gemini-1.0-Pro.", UserWarning)

        # Cost is $0.5 per million input tokens and $1.5 per million output tokens
        return 0.5 * input_tokens / 1e6 + 1.5 * output_tokens / 1e6


    def _concat_parts(self, parts: List[Part]) -> List:
        """Concatenate parts with the same type.
        If two adjacent parts both have the "text" attribute, then it will be joined into one part.
        """
        if not parts:
            return []

        concatenated_parts = []
        previous_part = parts[0]

        for current_part in parts[1:]:
            if previous_part.text != "":
                if self.use_vertexai:
                    previous_part = VertexAIPart.from_text(previous_part.text + current_part.text)
                else:
                    previous_part.text += current_part.text
            else:
                concatenated_parts.append(previous_part)
                previous_part = current_part

        if previous_part.text == "":
            if self.use_vertexai:
                previous_part = VertexAIPart.from_text("empty")
            else:
                previous_part.text = "empty"  # Empty content is not allowed.
        concatenated_parts.append(previous_part)

        return concatenated_parts
    
    def _oai_messages_to_gemini_messages(self, messages: list[Dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert messages from OAI format to Gemini format.
        Make sure the "user" role and "model" role are interleaved.
        Also, make sure the last item is from the "user" role.
        """
        prev_role = None
        rst = []
        curr_parts = []
        for i, message in enumerate(messages):
            # Since the tool call message does not have the "name" field, we need to find the corresponding tool message.
            if message["role"] == "tool":
                message["name"] = [
                    m for m in messages if "tool_calls" in m and m["tool_calls"][0]["id"] == message["tool_call_id"]
                ][0]["tool_calls"][0]["function"]["name"]

            parts = self._oai_content_to_gemini_content(message)
            role = "user" if message["role"] in ["user", "system"] else "model"

            if prev_role is None or role == prev_role:
                # If the message is a function call or a function response, we need to separate it from the previous message.
                if self.use_vertexai:
                    if parts[0].function_call or parts[0].function_response:
                        if len(curr_parts) > 1:
                            rst.append(VertexAIContent(parts=self._concat_parts(curr_parts), role=prev_role))
                        elif len(curr_parts) == 1:
                            rst.append(VertexAIContent(parts=curr_parts, role=None if curr_parts[0].function_response else role))
                        rst.append(VertexAIContent(parts=parts, role="function" if parts[0].function_response else role))
                        curr_parts = []
                    else:
                        curr_parts += parts
                else:
                    if "function_call" in parts[0] or "function_response" in parts[0]:
                        if len(curr_parts) > 1:
                            rst.append(Content(parts=self._concat_parts(curr_parts), role=prev_role))
                        elif len(curr_parts) == 1:
                            rst.append(Content(parts=curr_parts, role=None if curr_parts[0].function_response else role))
                        rst.append(Content(parts=parts, role="function" if parts[0].function_response else role))
                        curr_parts = []
                    else:
                        curr_parts += parts
            elif role != prev_role:
                if len(curr_parts) > 0:
                    if self.use_vertexai:
                        rst.append(VertexAIContent(parts=self._concat_parts(curr_parts), role=prev_role))
                    else:
                        rst.append(Content(parts=self._concat_parts(curr_parts), role=prev_role))
                curr_parts = parts
            # If the last message is a function response, it should be proceeded by a message from model instead of user.
            # So we will append a dummy message "continue" if the last message is a function response and the next message is from the user.
            if(len(rst) > 1 and rst[-1].role == "function" and len(messages) > (i + 1) and messages[i + 1]["role"] in ["user", "system"]):
                if self.use_vertexai:
                    rst.append(VertexAIContent(parts=self._oai_content_to_gemini_content("continue"), role="model"))
                else:
                    rst.append(Content(parts=self._oai_content_to_gemini_content("continue"), role="model"))
            prev_role = role

        # handle the last message
        if len(curr_parts) > 0:
            if self.use_vertexai:
                rst.append(VertexAIContent(parts=self._concat_parts(curr_parts), role=role))
            else:
                rst.append(Content(parts=self._concat_parts(curr_parts), role=role))

        # The Gemini is restrict on order of roles, such that
        # 1. The messages should be interleaved between user and model.
        # 2. The last message must be from the user role.
        # We add a dummy message "continue" if the last role is not the user.
        if rst[-1].role != "user" and rst[-1].role != "function":
            if self.use_vertexai:
                rst.append(VertexAIContent(parts=self._oai_content_to_gemini_content("continue"), role="user"))
            else:
                rst.append(Content(parts=self._oai_content_to_gemini_content("continue"), role="user"))
        return rst
    
    def _oai_tools_to_gemini_tools(self, tools: List[Dict[str, Any]]) -> List[Tool]:
        """Convert tools from OAI format to Gemini format."""
        if len(tools) == 0:
            return None
        function_declarations = []
        for tool in tools:
            if self.use_vertexai:
                function_declaration = VertexAIFunctionDeclaration(
                    name=tool["function"]["name"],
                    description=tool["function"]["description"],
                    parameters=tool["function"]["parameters"]
                )
            else:
                function_declaration = FunctionDeclaration(
                    name=tool["function"]["name"],
                    description=tool["function"]["description"],
                    parameters=self._oai_function_parameters_to_gemini_function_parameters(
                        copy.deepcopy(tool["function"]["parameters"])
                    ),
                )
            function_declarations.append(function_declaration)
        if self.use_vertexai:
            return [VertexAITool(function_declarations=function_declarations)]
        else:
            return [Tool(function_declarations=function_declarations)]


    def _oai_function_parameters_to_gemini_function_parameters(self, function_definition: dict[str, any]) -> dict[str, any]:
        """
        Convert OpenAPI function definition parameters to Gemini function parameters definition.
        The type key is renamed to type_ and the value is capitalized.
        """
        function_definition["type_"] = function_definition["type"].upper()
        del function_definition["type"]
        if "properties" in function_definition:
            for key in function_definition["properties"]:
                function_definition["properties"][key] = self._oai_function_parameters_to_gemini_function_parameters(
                    function_definition["properties"][key]
                )
        if "items" in function_definition:
            function_definition["items"] = self._oai_function_parameters_to_gemini_function_parameters(
                function_definition["items"]
            )
        return function_definition


    def _gemini_content_to_oai_choices(self, response: Content) -> List[Choice]:
        """Convert response from Gemini format to OAI format."""
        text = None
        tool_calls = None
        for part in response.parts:
            if part.function_call:
                if self.use_vertexai:
                    arguments = VertexAIPart.to_dict(part)["function_call"]["args"]
                else:
                    arguments = Part.to_dict(part)["function_call"]["args"]
                tool_calls = [
                    ChatCompletionMessageToolCall(
                        id=str(random.randint(0, 1000)),
                        type="function",
                        function=Function(
                            name=part.function_call.name,
                            arguments=json.dumps(arguments)
                        ),
                    )
                ]
            elif part.text:
                text = part.text
        message = ChatCompletionMessage(role="assistant", content=text, function_call=None, tool_calls=tool_calls)
        return [Choice(finish_reason="tool_calls" if tool_calls else "stop", index=0, message=message)]


def _to_pil(data: str) -> Image.Image:
    """
    Converts a base64 encoded image data string to a PIL Image object.

    This function first decodes the base64 encoded string to bytes, then creates a BytesIO object from the bytes,
    and finally creates and returns a PIL Image object from the BytesIO object.

    Parameters:
        data (str): The base64 encoded image data string.

    Returns:
        Image.Image: The PIL Image object created from the input data.
    """
    return Image.open(BytesIO(base64.b64decode(data)))


def get_image_data(image_file: str, use_b64=True) -> bytes:
    if image_file.startswith("http://") or image_file.startswith("https://"):
        response = requests.get(image_file)
        content = response.content
    elif re.match(r"data:image/(?:png|jpeg);base64,", image_file):
        return re.sub(r"data:image/(?:png|jpeg);base64,", "", image_file)
    else:
        image = Image.open(image_file).convert("RGB")
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        content = buffered.getvalue()

    if use_b64:
        return base64.b64encode(content).decode("utf-8")
    else:
        return content
