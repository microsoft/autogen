from __future__ import annotations

import copy
import inspect
import json
import os
import time
import warnings
from typing import Any, Dict, List, Tuple, Union

import boto3
from openai.types.chat import ChatCompletion, ChatCompletionMessageToolCall
from openai.types.chat.chat_completion import ChatCompletionMessage, Choice
from openai.types.completion_usage import CompletionUsage

from autogen.oai.client_utils import validate_parameter


class BedrockClient:
    """Client for Amazon's Bedrock API."""

    def __init__(self, **kwargs: Any):
        """Initialises BedrockClient for Amazon Bedrock Converse API

        Requires aws_access_key or environment variable, AWS_ACCESS_KEY, to be set
        Requires aws_secret_key or environment variable, AWS_SECRET_KEY, to be set
        Requires aws_region or environment variable, AWS_REGION, to be set

        Args (kwargs):
            aws_access_key Optional(str): The Amazon Bedrock Access key (or set environment variable AWS_ACCESS_KEY)
            aws_session_key Optional(str): The Amazon Bedrock Access key (or set environment variable AWS_ACCESS_KEY)
            aws_secret_key Optional(str): The Amazon Bedrock Access key (or set environment variable AWS_ACCESS_KEY)
            aws_region Optional(str): The Amazon Bedrock region (or set environment variable AWS_ACCESS_KEY)
        """
        self.aws_access_key = kwargs.get("aws_access_key", None)
        self.aws_session_key = kwargs.get("aws_session_key", None)
        self.aws_secret_key = kwargs.get("aws_secret_key", None)
        self.aws_region = kwargs.get("aws_region", None)

        if not self.aws_access_key:
            self.aws_access_key = os.getenv("AWS_ACCESS_KEY")

        if not self.aws_secret_key:
            self.aws_secret_key = os.getenv("AWS_SECRET_KEY")

        if not self.aws_region:
            self.aws_region = os.getenv("AWS_REGION")

        assert self.aws_access_key, "AWS_ACCESS_KEY is required, set the environment variable AWS_ACCESS_KEY"
        assert self.aws_secret_key, "AWS_SECRET_KEY is required, set the environment variable AWS_SECRET_KEY"
        assert self.aws_region, "AWS_REGION is required, set the environment variable AWS_REGION"

        self._client = boto3.client(
            "bedrock-runtime",
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key,
            region_name=self.aws_region,
        )

    @property
    def aws_access_key(self):
        return self.aws_access_key

    @property
    def aws_secret_key(self):
        return self.aws_secret_key

    @property
    def aws_region(self):
        return self.aws_region

    def parse_params(self, params: Dict[str, Any]) -> (Dict[str, Any], Dict[str, Any]):
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
            ["top_k", (int)],
            ["k", (int)],
        ]

        for param_name, suitable_types in additional_parameters:
            if param_name in params:
                additional_params[param_name] = validate_parameter(
                    params, param_name, suitable_types, False, None, None, None
                )

        # Default streaming to False
        if "stream" in params:
            self._streaming = params["stream"]
        else:
            self._streaming = False

        # Most models support tool calling with streaming
        # It is the responsibility of the developer to use a model
        # that supports streaming if they have streaming set to True

        """ Attempting to support streaming, otherwise we'll revert back.
        if bedrock_params["stream"]:
            warnings.warn(
                "Streaming is not currently supported, streaming will be disabled.",
                UserWarning,
            )
            bedrock_params["stream"] = False
        """

        return base_params, additional_params

    def create(self, params):
        """Run Amazon Bedrock inference and return AutoGen response"""

        base_params, additional_params = self.parse_params(params)

        messages, system_message = params.get("messages")

        request_payload = {
            "modelId": self._model_id,
            "messages": messages,
            "inferenceConfig": base_params,
        }

        if len(system_message) != 0:
            request_payload["system"] = system_message

        # Add in any model-specific parameters
        if len(additional_params) != 0:
            request_payload["additionalModelResponseFields"] = additional_params

        try:
            # Converse API here:
            # https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html
            #
            # Code examples here:
            # https://github.com/awsdocs/aws-doc-sdk-examples/tree/main/python/example_code/bedrock-runtime#code-examples

            response = self._client.converse(**request_payload)
        except self._client.exceptions.AccessDeniedException as e:
            print("Access denied: ", e)
        except self._client.exceptions.ResourceNotFoundException as e:
            print("Resource not found: ", e)
        except self._client.exceptions.ModelTimeoutException as e:
            print("Model timeout: ", e)
        except self._client.exceptions.InternalServerException as e:
            print("Internal server error: ", e)
        except Exception as e:
            print(f"An Error has occurred: {e}")

        if response is not None:
            prompt_tokens = response["usage"]["inputTokens"] if "usage" in response else 0
            completion_tokens = response["usage"]["outputTokens"] if "usage" in response else 0
            total_tokens = response["usage"]["totalTokens"] if "usage" in response else 0

            message_text = ""
            tool_calls = []

            if "output" in response and "message" in response["output"]:
                output_message = response["output"]
                for content in output_message["content"]:
                    if "text" in content:
                        message_text = content["text"]
                    elif "toolUse" in content:
                        tool_calls.append(
                            ChatCompletionMessageToolCall(
                                id=content["toolUse"]["toolUseId"],
                                function={
                                    "name": content["toolUse"]["name"],
                                    "arguments": json.dumps(content["toolUse"]["input"]),
                                },
                                type="function",
                            )
                        )

            stop_reason = {
                "end_turn": "stop",
                "tool_use": "tool_calls",
                "max_tokens": "length",
                "stop_sequence": "stop",
                "guardrail_intervened": "guardrail",
                "content_filtered": "filtered",
            }

            finish_reason = stop_reason.get(response["stopReason"], "stop")

            # Convert output back to OpenAI response format
            message = ChatCompletionMessage(
                role="assistant",
                content=message_text,
                function_call=None,
                tool_calls=tool_calls,
            )
            choices = [Choice(finish_reason=finish_reason, index=0, message=message)]

            response_oai = ChatCompletion(
                id=response.get("id", "unknown"),
                model=self._model_id,
                created=int(time.time()),
                object="chat.completion",
                choices=choices,
                usage=CompletionUsage(
                    prompt_tokens=prompt_tokens, completion_tokens=completion_tokens, total_tokens=total_tokens
                ),
            )

            return response_oai

    def cost(self):
        """
        AWS Bedrock supports a wide range of models
        """
        ...

    @staticmethod
    def get_usage_bedrock(response) -> Dict:
        """Get the usage of tokens and their cost information."""
        return {
            "prompt_tokens": response["usage"]["inputTokens"] if "usage" in response else 0,
            "completion_tokens": response["usage"]["outputTokens"] if "usage" in response else 0,
            "total_tokens": response["usage"]["totalTokens"] if "usage" in response else 0,
            "cost": response["metrics"]["latencyMs"] if "metrics" in response else 0.0,
            "model": response["model"],
        }


def oai_messages_to_converse_messages(messages: List[Dict[str, Any]]) -> (List[Dict[str, Any]], str):
    """Convert messages from OAI format to Amazon Bedrock's Converse format.

    We extract role='system' messages and return them as a string

    Returns:
        List[Dict[str, Any]]: List of chat messages
        str: system message
    """

    converse_messages = copy.deepcopy(messages)

    system_message = ""
    system_message_indexes = []

    # Build up the system messages
    for i, message in enumerate(converse_messages):
        if "role" in message and message["role"] == "system":
            system_message += ("\n" if len(system_message) != 0 else "") + message["content"]
            system_message_indexes.append(i)

    # Remove the system messages
    for i in system_message_indexes.reverse():
        converse_messages.pop(i)

    return converse_messages, system_message
