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


class AWSBedrock:
    def __init__(self, **kwargs: Any):
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

        self.client = boto3.client(
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

    def load_config(self, params):
        """
        Loads the valid parameters required to invoke the bedrock-runtime client converse.
        """

        bedrock_params = {}

        bedrock_params["model"] = params.get("model", None)
        assert bedrock_params["model"], "Please provide the 'model` in the config_list to use AWS Bedrock"

        bedrock_params["temperature"] = validate_parameter(
            params, "temperature", (float, int), False, 1.0, (0.0, 1.0), None
        )
        bedrock_params["top_p"] = validate_parameter(params, "top_p", (float, int), True, 0.8, (0.0, 1.0), None)
        bedrock_params["stop_sequences"] = validate_parameter(params, "stop_sequences", list, True, None, None, None)
        bedrock_params["max_tokens"] = validate_parameter(params, "max_tokens", int, False, 4096, (1, None), None)
        bedrock_params["stream"] = validate_parameter(params, "stream", bool, False, False, None, None)

        if bedrock_params["stream"]:
            warnings.warn(
                "Streaming is not currently supported, streaming will be disabled.",
                UserWarning,
            )
            bedrock_params["stream"] = False

        return bedrock_params

    def create(self, params):
        """ """

        bedrock_params = self.load_config(params)

        request_payload = {
            "modelId": bedrock_params["model"],
            "messages": params.get("messages", []),
            "inferenceConfig": {
                "maxTokens": bedrock_params["max_tokens"],
                "temperature": bedrock_params["temperature"],
                "topP": bedrock_params["top_p"],
                "stopSequences": bedrock_params["stop_sequences"],
            },
        }

        try:
            response = self.client.converse(**request_payload)
        except self.client.exceptions.AccessDeniedException as e:
            print("Access denied: ", e)
        except self.client.exceptions.ResourceNotFoundException as e:
            print("Resource not found: ", e)
        except self.client.exceptions.ModelTimeoutException as e:
            print("Model timeout: ", e)
        except self.client.exceptions.InternalServerException as e:
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
                model=bedrock_params["model"],
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
