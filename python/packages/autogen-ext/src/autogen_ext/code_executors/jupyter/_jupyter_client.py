from __future__ import annotations

import sys
from dataclasses import dataclass
from types import TracebackType
from typing import Any, AsyncGenerator, cast

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

import datetime
import json
import uuid

import requests
from requests.adapters import HTTPAdapter, Retry
from websockets.asyncio.client import ClientConnection, connect

from ._jupyter_connection_info import JupyterConnectionInfo


class JupyterClient:
    def __init__(self, connection_info: JupyterConnectionInfo):
        """(Experimental) A client for communicating with a Jupyter gateway server.

        Args:
            connection_info (JupyterConnectionInfo): Connection information
        """
        self._connection_info = connection_info
        self._session = requests.Session()
        retries = Retry(total=5, backoff_factor=0.1)
        self._session.mount("http://", HTTPAdapter(max_retries=retries))

    def _get_headers(self) -> dict[str, str]:
        if self._connection_info.token is None:
            return {}
        return {"Authorization": f"token {self._connection_info.token}"}

    def _get_cookies(self) -> str:
        cookies = self._session.cookies.get_dict()
        return "; ".join([f"{name}={value}" for name, value in cookies.items()])

    def _get_api_base_url(self) -> str:
        protocol = "https" if self._connection_info.use_https else "http"
        port = f":{self._connection_info.port}" if self._connection_info.port else ""
        return f"{protocol}://{self._connection_info.host}{port}"

    def _get_ws_base_url(self) -> str:
        port = f":{self._connection_info.port}" if self._connection_info.port else ""
        return f"ws://{self._connection_info.host}{port}"

    def list_kernel_specs(self) -> dict[str, dict[str, str]]:
        response = self._session.get(
            f"{self._get_api_base_url()}/api/kernelspecs", headers=self._get_headers()
        )
        return cast(dict[str, dict[str, str]], response.json())

    def list_kernels(self) -> list[dict[str, str]]:
        response = self._session.get(
            f"{self._get_api_base_url()}/api/kernels", headers=self._get_headers()
        )
        return cast(list[dict[str, str]], response.json())

    def start_kernel(self, kernel_spec_name: str) -> str:
        """Start a new kernel.

        Args:
            kernel_spec_name (str): Name of the kernel spec to start

        Returns:
            str: ID of the started kernel
        """

        response = self._session.post(
            f"{self._get_api_base_url()}/api/kernels",
            headers=self._get_headers(),
            json={"name": kernel_spec_name},
        )
        return cast(str, response.json()["id"])

    def delete_kernel(self, kernel_id: str) -> None:
        response = self._session.delete(
            f"{self._get_api_base_url()}/api/kernels/{kernel_id}",
            headers=self._get_headers(),
        )
        response.raise_for_status()

    def restart_kernel(self, kernel_id: str) -> None:
        response = self._session.post(
            f"{self._get_api_base_url()}/api/kernels/{kernel_id}/restart",
            headers=self._get_headers(),
        )
        response.raise_for_status()

    async def get_kernel_client(self, kernel_id: str) -> JupyterKernelClient:
        ws_url = f"{self._get_ws_base_url()}/api/kernels/{kernel_id}/channels"
        headers = self._get_headers()
        headers["Cookie"] = self._get_cookies()
        websocket = await connect(
            ws_url,
            additional_headers=headers,
            max_size=2**24,
            open_timeout=120,
            ping_timeout=30,
            close_timeout=30,
        )
        return JupyterKernelClient(websocket)


class JupyterKernelClient:
    """A client for communicating with a Jupyter kernel."""

    @dataclass
    class ExecutionResult:
        @dataclass
        class DataItem:
            mime_type: str
            data: str

        is_ok: bool
        output: str
        data_items: list[DataItem]

    def __init__(self, websocket: ClientConnection):
        self._session_id: str = uuid.uuid4().hex
        self._websocket = websocket

    async def _send_message(
        self, *, content: dict[str, Any], channel: str, message_type: str
    ) -> str:
        timestamp = datetime.datetime.now().isoformat()
        message_id = uuid.uuid4().hex
        message = {
            "header": {
                "username": "autogen",
                "version": "5.0",
                "session": self._session_id,
                "msg_id": message_id,
                "msg_type": message_type,
                "date": timestamp,
            },
            "parent_header": {},
            "channel": channel,
            "content": content,
            "metadata": {},
            "buffers": {},
        }
        await self._websocket.send(json.dumps(message))
        return message_id

    async def wait_for_ready(self) -> None:
        message_id = await self._send_message(
            content={}, channel="shell", message_type="kernel_info_request"
        )

        async for message in self._receive_message(message_id):
            if message["msg_type"] == "kernel_info_reply":
                break

    async def execute(self, code: str) -> ExecutionResult:
        message_id = await self._send_message(
            content={
                "code": code,
                "silent": False,
                "store_history": True,
                "user_expressions": {},
                "allow_stdin": False,
                "stop_on_error": True,
            },
            channel="shell",
            message_type="execute_request",
        )

        text_output: list[str] = []
        data_output: list[JupyterKernelClient.ExecutionResult.DataItem] = []

        async for message in self._receive_message(message_id):
            content = message["content"]
            match message["msg_type"]:
                case "execute_result" | "display_data":
                    for data_type, data in content["data"].items():
                        match data_type:
                            case "text/plain":
                                text_output.append(data)
                            case type if type.startswith(
                                "image/"
                            ) or type == "text/html":
                                data_output.append(
                                    self.ExecutionResult.DataItem(
                                        mime_type=data_type, data=data
                                    )
                                )
                            case _:
                                text_output.append(json.dumps(data))
                case "stream":
                    text_output.append(content["text"])
                case "error":
                    return JupyterKernelClient.ExecutionResult(
                        is_ok=False,
                        output="\n".join(content["traceback"]),
                        data_items=[],
                    )
                case _:
                    pass

            if message["msg_type"] == "status" and content["execution_state"] == "idle":
                break

        return JupyterKernelClient.ExecutionResult(
            is_ok=True,
            output="\n".join([output for output in text_output]),
            data_items=data_output,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self._websocket.close()

    async def _receive_message(self, message_id: str) -> AsyncGenerator[dict[str, Any]]:
        async for data in self._websocket:
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            message = cast(dict[str, Any], json.loads(data))
            if message.get("parent_header", {}).get("msg_id") == message_id:
                yield message
