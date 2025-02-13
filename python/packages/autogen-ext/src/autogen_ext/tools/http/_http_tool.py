import re
from typing import Any, Literal, Optional, Type

import httpx
from autogen_core import CancellationToken, Component
from autogen_core.tools import BaseTool
from json_schema_to_pydantic import create_model
from pydantic import BaseModel, Field
from typing_extensions import Self


class HttpToolConfig(BaseModel):
    name: str
    """
    The name of the tool.
    """
    description: Optional[str]
    """
    A description of the tool.
    """
    scheme: Literal["http", "https"] = "http"
    """
    The scheme to use for the request.
    """
    host: str
    """
    The URL to send the request to.
    """
    port: int
    """
    The port to send the request to.
    """
    path: str = Field(default="/")
    """
    The path to send the request to. defaults to "/"
    The path can accept parameters, e.g. "/{param1}/{param2}".
    These parameters will be templated from the inputs args, any additional parameters will be added as query parameters or the body of the request.
    """
    method: Optional[Literal["GET", "POST", "PUT", "DELETE", "PATCH"]] = "POST"
    """
    The HTTP method to use, will default to POST if not provided.
    """
    headers: Optional[dict[str, Any]]
    """
    A dictionary of headers to send with the request.
    """
    json_schema: dict[str, Any]
    """
    A JSON Schema object defining the expected parameters for the tool.
    Path parameters MUST also be included in the json_schema. They must also MUST be set to string
    """
    return_type: Optional[Literal["text", "json"]] = "text"
    """
    The type of response to return from the tool.
    """


class HttpTool(BaseTool[BaseModel, Any], Component[HttpToolConfig]):
    """A wrapper for using an HTTP server as a tool.

    Args:
        name (str): The name of the tool.
        description (str, optional): A description of the tool.
        scheme (str): The scheme to use for the request. Must be either "http" or "https".
        host (str): The host to send the request to.
        port (int): The port to send the request to.
        path (str, optional): The path to send the request to. Defaults to "/".
            Can include path parameters like "/{param1}/{param2}" which will be templated from input args.
        method (str, optional): The HTTP method to use, will default to POST if not provided.
            Must be one of "GET", "POST", "PUT", "DELETE", "PATCH".
        headers (dict[str, Any], optional): A dictionary of headers to send with the request.
        json_schema (dict[str, Any]): A JSON Schema object defining the expected parameters for the tool.
            Path parameters must also be included in the schema and must be strings.
        return_type (Literal["text", "json"], optional): The type of response to return from the tool.
            Defaults to "text".

    .. note::
        This tool requires the :code:`http-tool` extra for the :code:`autogen-ext` package.

        To install:

        .. code-block:: bash

            pip install -U "autogen-agentchat" "autogen-ext[http-tool]"

    Example:
        Simple use case::

          import asyncio

          from autogen_agentchat.agents import AssistantAgent
          from autogen_agentchat.messages import TextMessage
          from autogen_core import CancellationToken
          from autogen_ext.models.openai import OpenAIChatCompletionClient
          from autogen_ext.tools.http import HttpTool

          # Define a JSON schema for a base64 decode tool
          base64_schema = {
              "type": "object",
              "properties": {
                  "value": {"type": "string", "description": "The base64 value to decode"},
              },
              "required": ["value"],
          }

          # Create an HTTP tool for the httpbin API
          base64_tool = HttpTool(
              name="base64_decode",
              description="base64 decode a value",
              scheme="https",
              host="httpbin.org",
              port=443,
              path="/base64/{value}",
              method="GET",
              json_schema=base64_schema,
          )


          async def main():
              # Create an assistant with the base64 tool
              model = OpenAIChatCompletionClient(model="gpt-4")
              assistant = AssistantAgent("base64_assistant", model_client=model, tools=[base64_tool])

              # The assistant can now use the base64 tool to decode the string
              response = await assistant.on_messages(
                  [TextMessage(content="Can you base64 decode the value 'YWJjZGU=', please?", source="user")],
                  CancellationToken(),
              )
              print(response.chat_message.content)


          asyncio.run(main())
    """

    component_type = "tool"
    component_provider_override = "autogen_ext.tools.http.HttpTool"
    component_config_schema = HttpToolConfig

    def __init__(
        self,
        name: str,
        host: str,
        port: int,
        json_schema: dict[str, Any],
        headers: Optional[dict[str, Any]] = None,
        description: str = "HTTP tool",
        path: str = "/",
        scheme: Literal["http", "https"] = "http",
        method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = "POST",
        return_type: Literal["text", "json"] = "text",
    ) -> None:
        self.server_params = HttpToolConfig(
            name=name,
            description=description,
            host=host,
            port=port,
            path=path,
            scheme=scheme,
            method=method,
            headers=headers,
            json_schema=json_schema,
            return_type=return_type,
        )

        # Use regex to find all path parameters, we will need those later to template the path
        path_params = {match.group(1) for match in re.finditer(r"{([^}]*)}", path)}
        self._path_params = path_params

        # Create the input model from the modified schema
        input_model = create_model(json_schema)

        # Use Any as return type since HTTP responses can vary
        base_return_type: Type[Any] = object

        super().__init__(input_model, base_return_type, name, description)

    def _to_config(self) -> HttpToolConfig:
        copied_config = self.server_params.model_copy()
        return copied_config

    @classmethod
    def _from_config(cls, config: HttpToolConfig) -> Self:
        copied_config = config.model_copy().model_dump()
        return cls(**copied_config)

    async def run(self, args: BaseModel, cancellation_token: CancellationToken) -> Any:
        """Execute the HTTP tool with the given arguments.

        Args:
            args: The validated input arguments
            cancellation_token: Token for cancelling the operation

        Returns:
            The response body from the HTTP call in JSON format

        Raises:
            Exception: If tool execution fails
        """

        model_dump = args.model_dump()
        path_params = {k: v for k, v in model_dump.items() if k in self._path_params}
        # Remove path params from the model dump
        for k in self._path_params:
            model_dump.pop(k)

        path = self.server_params.path.format(**path_params)

        url = httpx.URL(
            scheme=self.server_params.scheme,
            host=self.server_params.host,
            port=self.server_params.port,
            path=path,
        )
        async with httpx.AsyncClient() as client:
            match self.server_params.method:
                case "GET":
                    response = await client.get(url, params=model_dump)
                case "PUT":
                    response = await client.put(url, json=model_dump)
                case "DELETE":
                    response = await client.delete(url, params=model_dump)
                case "PATCH":
                    response = await client.patch(url, json=model_dump)
                case _:  # Default case POST
                    response = await client.post(url, json=model_dump)

        match self.server_params.return_type:
            case "text":
                return response.text
            case "json":
                return response.json()
            case _:
                raise ValueError(f"Invalid return type: {self.server_params.return_type}")
