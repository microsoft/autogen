"""
Create a compatible client for the Amazon Bedrock Converse API.

Example usage:
Install the `boto3` package by running `pip install --upgrade boto3`.
- https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html

import autogen

config_list = [
    {
        "api_type": "bedrock",
        "model": "meta.llama3-1-8b-instruct-v1:0",
        "aws_region": "us-west-2",
        "aws_access_key": "",
        "aws_secret_key": "",
        "price" : [0.003, 0.015]
    }
]

assistant = autogen.AssistantAgent("assistant", llm_config={"config_list": config_list})

"""

from __future__ import annotations

import base64
import json
import os
import re
import time
import warnings
from typing import Any, Dict, List, Literal, Tuple

import boto3
import requests
from botocore.config import Config
from openai.types.chat import ChatCompletion, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion import ChatCompletionMessage, Choice
from openai.types.completion_usage import CompletionUsage

from autogen.oai.client_utils import validate_parameter


class BedrockClient:
    """Client for Amazon's Bedrock Converse API."""

    _retries = 5

    def __init__(self, **kwargs: Any):
        """
        Initialises BedrockClient for Amazon's Bedrock Converse API
        """
        self._aws_access_key = kwargs.get("aws_access_key", None)
        self._aws_secret_key = kwargs.get("aws_secret_key", None)
        self._aws_session_token = kwargs.get("aws_session_token", None)
        self._aws_region = kwargs.get("aws_region", None)
        self._aws_profile_name = kwargs.get("aws_profile_name", None)

        if not self._aws_access_key:
            self._aws_access_key = os.getenv("AWS_ACCESS_KEY")

        if not self._aws_secret_key:
            self._aws_secret_key = os.getenv("AWS_SECRET_KEY")

        if not self._aws_session_token:
            self._aws_session_token = os.getenv("AWS_SESSION_TOKEN")

        if not self._aws_region:
            self._aws_region = os.getenv("AWS_REGION")

        if self._aws_region is None:
            raise ValueError("Region is required to use the Amazon Bedrock API.")

        # Initialize Bedrock client, session, and runtime
        bedrock_config = Config(
            region_name=self._aws_region,
            signature_version="v4",
            retries={"max_attempts": self._retries, "mode": "standard"},
        )

        session = boto3.Session(
            aws_access_key_id=self._aws_access_key,
            aws_secret_access_key=self._aws_secret_key,
            aws_session_token=self._aws_session_token,
            profile_name=self._aws_profile_name,
        )

        self.bedrock_runtime = session.client(service_name="bedrock-runtime", config=bedrock_config)

    def message_retrieval(self, response):
        """Retrieve the messages from the response."""
        return [choice.message for choice in response.choices]

    def parse_custom_params(self, params: Dict[str, Any]):
        """
        Parses custom parameters for logic in this client class
        """

        # Should we separate system messages into its own request parameter, default is True
        # This is required because not all models support a system prompt (e.g. Mistral Instruct).
        self._supports_system_prompts = params.get("supports_system_prompts", True)

    def parse_params(self, params: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Loads the valid parameters required to invoke Bedrock Converse
        Returns a tuple of (base_params, additional_params)
        """

        base_params = {}
        additional_params = {}

        # Amazon Bedrock  base model IDs are here:
        # https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html
        self._model_id = params.get("model", None)
        assert self._model_id, "Please provide the 'model` in the config_list to use Amazon Bedrock"

        # Parameters vary based on the model used.
        # As we won't cater for all models and parameters, it's the developer's
        # responsibility to implement the parameters and they will only be
        # included if the developer has it in the config.
        #
        # Important:
        # No defaults will be used (as they can vary per model)
        # No ranges will be used (as they can vary)
        # We will cover all the main parameters but there may be others
        # that need to be added later
        #
        # Here are some pages that show the parameters available for different models
        # https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-titan-text.html
        # https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-text-completion.html
        # https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-cohere-command-r-plus.html
        # https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-meta.html
        # https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-mistral-chat-completion.html

        # Here are the possible "base" parameters and their suitable types
        base_parameters = [["temperature", (float, int)], ["topP", (float, int)], ["maxTokens", (int)]]

        for param_name, suitable_types in base_parameters:
            if param_name in params:
                base_params[param_name] = validate_parameter(
                    params, param_name, suitable_types, False, None, None, None
                )

        # Here are the possible "model-specific" parameters and their suitable types, known as additional parameters
        additional_parameters = [
            ["top_p", (float, int)],
            ["top_k", (int)],
            ["k", (int)],
            ["seed", (int)],
        ]

        for param_name, suitable_types in additional_parameters:
            if param_name in params:
                additional_params[param_name] = validate_parameter(
                    params, param_name, suitable_types, False, None, None, None
                )

        # Streaming
        if "stream" in params:
            self._streaming = params["stream"]
        else:
            self._streaming = False

        # For this release we will not support streaming as many models do not support streaming with tool use
        if self._streaming:
            warnings.warn(
                "Streaming is not currently supported, streaming will be disabled.",
                UserWarning,
            )
            self._streaming = False

        return base_params, additional_params

    def create(self, params):
        """Run Amazon Bedrock inference and return AutoGen response"""

        # Set custom client class settings
        self.parse_custom_params(params)

        # Parse the inference parameters
        base_params, additional_params = self.parse_params(params)

        has_tools = "tools" in params
        messages = oai_messages_to_bedrock_messages(params["messages"], has_tools, self._supports_system_prompts)

        if self._supports_system_prompts:
            system_messages = extract_system_messages(params["messages"])

        tool_config = format_tools(params["tools"] if has_tools else [])

        request_args = {"messages": messages, "modelId": self._model_id}

        # Base and additional args
        if len(base_params) > 0:
            request_args["inferenceConfig"] = base_params

        if len(additional_params) > 0:
            request_args["additionalModelRequestFields"] = additional_params

        if self._supports_system_prompts:
            request_args["system"] = system_messages

        if len(tool_config["tools"]) > 0:
            request_args["toolConfig"] = tool_config

        try:
            response = self.bedrock_runtime.converse(
                **request_args,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to get response from Bedrock: {e}")

        if response is None:
            raise RuntimeError(f"Failed to get response from Bedrock after retrying {self._retries} times.")

        finish_reason = convert_stop_reason_to_finish_reason(response["stopReason"])
        response_message = response["output"]["message"]

        if finish_reason == "tool_calls":
            tool_calls = format_tool_calls(response_message["content"])
            # text = ""
        else:
            tool_calls = None

        text = ""
        for content in response_message["content"]:
            if "text" in content:
                text = content["text"]
                # NOTE: other types of output may be dealt with here

        message = ChatCompletionMessage(role="assistant", content=text, tool_calls=tool_calls)

        response_usage = response["usage"]
        usage = CompletionUsage(
            prompt_tokens=response_usage["inputTokens"],
            completion_tokens=response_usage["outputTokens"],
            total_tokens=response_usage["totalTokens"],
        )

        return ChatCompletion(
            id=response["ResponseMetadata"]["RequestId"],
            choices=[Choice(finish_reason=finish_reason, index=0, message=message)],
            created=int(time.time()),
            model=self._model_id,
            object="chat.completion",
            usage=usage,
        )

    def cost(self, response: ChatCompletion) -> float:
        """Calculate the cost of the response."""
        return calculate_cost(response.usage.prompt_tokens, response.usage.completion_tokens, response.model)

    @staticmethod
    def get_usage(response) -> Dict:
        """Get the usage of tokens and their cost information."""
        return {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "cost": response.cost,
            "model": response.model,
        }


def extract_system_messages(messages: List[dict]) -> List:
    """Extract the system messages from the list of messages.

    Args:
        messages (list[dict]): List of messages.

    Returns:
        List[SystemMessage]: List of System messages.
    """

    """
    system_messages = [message.get("content")[0]["text"] for message in messages if message.get("role") == "system"]
    return system_messages # ''.join(system_messages)
    """

    for message in messages:
        if message.get("role") == "system":
            if isinstance(message["content"], str):
                return [{"text": message.get("content")}]
            else:
                return [{"text": message.get("content")[0]["text"]}]
    return []


def oai_messages_to_bedrock_messages(
    messages: List[Dict[str, Any]], has_tools: bool, supports_system_prompts: bool
) -> List[Dict]:
    """
    Convert messages from OAI format to Bedrock format.
    We correct for any specific role orders and types, etc.
    AWS Bedrock requires messages to alternate between user and assistant roles. This function ensures that the messages
    are in the correct order and format for Bedrock by inserting "Please continue" messages as needed.
    This is the same method as the one in the Autogen Anthropic client
    """

    # Track whether we have tools passed in. If not,  tool use / result messages should be converted to text messages.
    # Bedrock requires a tools parameter with the tools listed, if there are other messages with tool use or tool results.
    # This can occur when we don't need tool calling, such as for group chat speaker selection

    # Convert messages to Bedrock compliant format

    # Take out system messages if the model supports it, otherwise leave them in.
    if supports_system_prompts:
        messages = [x for x in messages if not x["role"] == "system"]
    else:
        # Replace role="system" with role="user"
        for msg in messages:
            if msg["role"] == "system":
                msg["role"] = "user"

    processed_messages = []

    # Used to interweave user messages to ensure user/assistant alternating
    user_continue_message = {"content": [{"text": "Please continue."}], "role": "user"}
    assistant_continue_message = {
        "content": [{"text": "Please continue."}],
        "role": "assistant",
    }

    tool_use_messages = 0
    tool_result_messages = 0
    last_tool_use_index = -1
    last_tool_result_index = -1
    # user_role_index = 0 if supports_system_prompts else 1 # If system prompts are supported, messages start with user, otherwise they'll be the second message
    for message in messages:
        # New messages will be added here, manage role alternations
        expected_role = "user" if len(processed_messages) % 2 == 0 else "assistant"

        if "tool_calls" in message:
            # Map the tool call options to Bedrock's format
            tool_uses = []
            tool_names = []
            for tool_call in message["tool_calls"]:
                tool_uses.append(
                    {
                        "toolUse": {
                            "toolUseId": tool_call["id"],
                            "name": tool_call["function"]["name"],
                            "input": json.loads(tool_call["function"]["arguments"]),
                        }
                    }
                )
                if has_tools:
                    tool_use_messages += 1
                tool_names.append(tool_call["function"]["name"])

            if expected_role == "user":
                # Insert an extra user message as we will append an assistant message
                processed_messages.append(user_continue_message)

            if has_tools:
                processed_messages.append({"role": "assistant", "content": tool_uses})
                last_tool_use_index = len(processed_messages) - 1
            else:
                # Not using tools, so put in a plain text message
                processed_messages.append(
                    {
                        "role": "assistant",
                        "content": [
                            {"text": f"Some internal function(s) that could be used: [{', '.join(tool_names)}]"}
                        ],
                    }
                )
        elif "tool_call_id" in message:
            if has_tools:
                # Map the tool usage call to tool_result for Bedrock
                tool_result = {
                    "toolResult": {
                        "toolUseId": message["tool_call_id"],
                        "content": [{"text": message["content"]}],
                    }
                }

                # If the previous message also had a tool_result, add it to that
                # Otherwise append a new message
                if last_tool_result_index == len(processed_messages) - 1:
                    processed_messages[-1]["content"].append(tool_result)
                else:
                    if expected_role == "assistant":
                        # Insert an extra assistant message as we will append a user message
                        processed_messages.append(assistant_continue_message)

                    processed_messages.append({"role": "user", "content": [tool_result]})
                    last_tool_result_index = len(processed_messages) - 1

                tool_result_messages += 1
            else:
                # Not using tools, so put in a plain text message
                processed_messages.append(
                    {
                        "role": "user",
                        "content": [{"text": f"Running the function returned: {message['content']}"}],
                    }
                )
        elif message["content"] == "":
            # Ignoring empty messages
            pass
        else:
            if expected_role != message["role"] and not (len(processed_messages) == 0 and message["role"] == "system"):
                # Inserting the alternating continue message (ignore if it's the first message and a system message)
                processed_messages.append(
                    user_continue_message if expected_role == "user" else assistant_continue_message
                )

            processed_messages.append(
                {
                    "role": message["role"],
                    "content": parse_content_parts(message=message),
                }
            )

    # We'll replace the last tool_use if there's no tool_result (occurs if we finish the conversation before running the function)
    if has_tools and tool_use_messages != tool_result_messages:
        processed_messages[last_tool_use_index] = assistant_continue_message

    # name is not a valid field on messages
    for message in processed_messages:
        if "name" in message:
            message.pop("name", None)

    # Note: When using reflection_with_llm we may end up with an "assistant" message as the last message and that may cause a blank response
    # So, if the last role is not user, add a 'user' continue message at the end
    if processed_messages[-1]["role"] != "user":
        processed_messages.append(user_continue_message)

    return processed_messages


def parse_content_parts(
    message: Dict[str, Any],
) -> List[dict]:
    content: str | List[Dict[str, Any]] = message.get("content")
    if isinstance(content, str):
        return [
            {
                "text": content,
            }
        ]
    content_parts = []
    for part in content:
        # part_content: Dict = part.get("content")
        if "text" in part:  # part_content:
            content_parts.append(
                {
                    "text": part.get("text"),
                }
            )
        elif "image_url" in part:  # part_content:
            image_data, content_type = parse_image(part.get("image_url").get("url"))
            content_parts.append(
                {
                    "image": {
                        "format": content_type[6:],  # image/
                        "source": {"bytes": image_data},
                    },
                }
            )
        else:
            # Ignore..
            continue
    return content_parts


def parse_image(image_url: str) -> Tuple[bytes, str]:
    """Try to get the raw data from an image url.

    Ref: https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ImageSource.html
    returns a tuple of (Image Data, Content Type)
    """
    pattern = r"^data:(image/[a-z]*);base64,\s*"
    content_type = re.search(pattern, image_url)
    # if already base64 encoded.
    # Only supports 'image/jpeg', 'image/png', 'image/gif' or 'image/webp'
    if content_type:
        image_data = re.sub(pattern, "", image_url)
        return base64.b64decode(image_data), content_type.group(1)

    # Send a request to the image URL
    response = requests.get(image_url)
    # Check if the request was successful
    if response.status_code == 200:

        content_type = response.headers.get("Content-Type")
        if not content_type.startswith("image"):
            content_type = "image/jpeg"
        # Get the image content
        image_content = response.content
        return image_content, content_type
    else:
        raise RuntimeError("Unable to access the image url")


def format_tools(tools: List[Dict[str, Any]]) -> Dict[Literal["tools"], List[Dict[str, Any]]]:
    converted_schema = {"tools": []}

    for tool in tools:
        if tool["type"] == "function":
            function = tool["function"]
            converted_tool = {
                "toolSpec": {
                    "name": function["name"],
                    "description": function["description"],
                    "inputSchema": {"json": {"type": "object", "properties": {}, "required": []}},
                }
            }

            for prop_name, prop_details in function["parameters"]["properties"].items():
                converted_tool["toolSpec"]["inputSchema"]["json"]["properties"][prop_name] = {
                    "type": prop_details["type"],
                    "description": prop_details.get("description", ""),
                }
                if "enum" in prop_details:
                    converted_tool["toolSpec"]["inputSchema"]["json"]["properties"][prop_name]["enum"] = prop_details[
                        "enum"
                    ]
                if "default" in prop_details:
                    converted_tool["toolSpec"]["inputSchema"]["json"]["properties"][prop_name]["default"] = (
                        prop_details["default"]
                    )

            if "required" in function["parameters"]:
                converted_tool["toolSpec"]["inputSchema"]["json"]["required"] = function["parameters"]["required"]

            converted_schema["tools"].append(converted_tool)

    return converted_schema


def format_tool_calls(content):
    """Converts Converse API response tool calls to AutoGen format"""
    tool_calls = []
    for tool_request in content:
        if "toolUse" in tool_request:
            tool = tool_request["toolUse"]

            tool_calls.append(
                ChatCompletionMessageToolCall(
                    id=tool["toolUseId"],
                    function={
                        "name": tool["name"],
                        "arguments": json.dumps(tool["input"]),
                    },
                    type="function",
                )
            )
    return tool_calls


def convert_stop_reason_to_finish_reason(
    stop_reason: str,
) -> Literal["stop", "length", "tool_calls", "content_filter"]:
    """
    Converts Bedrock finish reasons to our finish reasons, according to OpenAI:

    - stop: if the model hit a natural stop point or a provided stop sequence,
    - length: if the maximum number of tokens specified in the request was reached,
    - content_filter: if content was omitted due to a flag from our content filters,
    - tool_calls: if the model called a tool
    """
    if stop_reason:
        finish_reason_mapping = {
            "tool_use": "tool_calls",
            "finished": "stop",
            "end_turn": "stop",
            "max_tokens": "length",
            "stop_sequence": "stop",
            "complete": "stop",
            "content_filtered": "content_filter",
        }
        return finish_reason_mapping.get(stop_reason.lower(), stop_reason.lower())

    warnings.warn(f"Unsupported stop reason: {stop_reason}", UserWarning)
    return None


# NOTE: As this will be quite dynamic, it's expected that the developer will use the "price" parameter in their config
# These may be removed.
PRICES_PER_K_TOKENS = {
    "meta.llama3-8b-instruct-v1:0": (0.0003, 0.0006),
    "meta.llama3-70b-instruct-v1:0": (0.00265, 0.0035),
    "mistral.mistral-7b-instruct-v0:2": (0.00015, 0.0002),
    "mistral.mixtral-8x7b-instruct-v0:1": (0.00045, 0.0007),
    "mistral.mistral-large-2402-v1:0": (0.004, 0.012),
    "mistral.mistral-small-2402-v1:0": (0.001, 0.003),
}


def calculate_cost(input_tokens: int, output_tokens: int, model_id: str) -> float:
    """Calculate the cost of the completion using the Bedrock pricing."""

    if model_id in PRICES_PER_K_TOKENS:
        input_cost_per_k, output_cost_per_k = PRICES_PER_K_TOKENS[model_id]
        input_cost = (input_tokens / 1000) * input_cost_per_k
        output_cost = (output_tokens / 1000) * output_cost_per_k
        return input_cost + output_cost
    else:
        warnings.warn(
            f'Cannot get the costs for {model_id}. The cost will be 0. In your config_list, add field {{"price" : [prompt_price_per_1k, completion_token_price_per_1k]}} for customized pricing.',
            UserWarning,
        )
        return 0
