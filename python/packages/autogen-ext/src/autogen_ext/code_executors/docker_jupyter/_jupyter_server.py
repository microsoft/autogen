from __future__ import annotations
import docker # type: ignore
import atexit
import io
import logging
import secrets
import sys
import uuid
import os
from pathlib import Path
from types import TracebackType
from typing import Dict, Optional, Type, Union, Any, List, cast, Protocol, runtime_checkable
from dataclasses import dataclass
import datetime
import json
import requests
import asyncio
import aiohttp # type: ignore
from requests.adapters import HTTPAdapter, Retry
import websockets # type: ignore
from time import sleep
if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

@dataclass
class JupyterConnectionInfo:
    """(Experimental)"""

    host: str
    """`str` - Host of the Jupyter gateway server"""
    use_https: bool
    """`bool` - Whether to use HTTPS"""
    port: Optional[int] = None
    """`Optional[int]` - Port of the Jupyter gateway server. If None, the default port is used"""
    token: Optional[str] = None
    """`Optional[str]` - Token for authentication. If None, no token is used"""


@runtime_checkable
class JupyterConnectable(Protocol):
    """(Experimental)"""

    @property
    def connection_info(self) -> JupyterConnectionInfo:
        """Return the connection information for this connectable."""
        pass

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
        # Create aiohttp session for async requests
        self._async_session = None
    
    async def _ensure_async_session(self) -> aiohttp.ClientSession:
        if self._async_session is None:
            self._async_session = aiohttp.ClientSession()
        return self._async_session

    def _get_headers(self) -> Dict[str, str]:
        if self._connection_info.token is None:
            return {}
        return {"Authorization": f"token {self._connection_info.token}"}

    def _get_api_base_url(self) -> str:
        protocol = "https" if self._connection_info.use_https else "http"
        port = f":{self._connection_info.port}" if self._connection_info.port else ""
        return f"{protocol}://{self._connection_info.host}{port}"

    def _get_ws_base_url(self) -> str:
        port = f":{self._connection_info.port}" if self._connection_info.port else ""
        return f"ws://{self._connection_info.host}{port}"


    async def list_kernel_specs(self) -> Dict[str, Dict[str, str]]:
        response = self._session.get(f"{self._get_api_base_url()}/api/kernelspecs", headers=self._get_headers())
        return cast(Dict[str, Dict[str, str]], response.json())

    async def list_kernels(self) -> List[Dict[str, str]]:
        response = self._session.get(f"{self._get_api_base_url()}/api/kernels", headers=self._get_headers())
        return cast(List[Dict[str, str]], response.json())

    async def start_kernel(self, kernel_spec_name: str) -> str:
        """Start a new kernel asynchronously.

        Args:
            kernel_spec_name (str): Name of the kernel spec to start

        Returns:
            str: ID of the started kernel
        """
        session = await self._ensure_async_session()
        async with session.post(
            f"{self._get_api_base_url()}/api/kernels",
            headers=self._get_headers(),
            json={"name": kernel_spec_name},
        ) as response:
            data = await response.json()
            return cast(str, data["id"])
        
    async def delete_kernel(self, kernel_id: str) -> None:
        session = await self._ensure_async_session()
        async with session.delete(
            f"{self._get_api_base_url()}/api/kernels/{kernel_id}", headers=self._get_headers()
        ) as response:
            response.raise_for_status()

    async def restart_kernel(self, kernel_id: str) -> None:
        session = await self._ensure_async_session()
        async with session.post(
            f"{self._get_api_base_url()}/api/kernels/{kernel_id}/restart", headers=self._get_headers()
        ) as response:
            response.raise_for_status()

    async def get_kernel_client(self, kernel_id: str) -> JupyterKernelClient:
        ws_url = f"{self._get_ws_base_url()}/api/kernels/{kernel_id}/channels"
        # Using websockets library for async websocket connections
        ws = await websockets.connect(ws_url, extra_headers=self._get_headers())
        return JupyterKernelClient(ws)
    
    async def close(self) -> None:
        """Close the async session"""
        if self._async_session is not None:
            await self._async_session.close()
            self._async_session = None
        self._session.close()

class JupyterKernelClient:
    """An asynchronous client for communicating with a Jupyter kernel."""

    @dataclass
    class ExecutionResult:
        @dataclass
        class DataItem:
            mime_type: str
            data: str

        is_ok: bool
        output: str
        data_items: List[DataItem]

    def __init__(self, websocket):
        self._session_id: str = uuid.uuid4().hex
        self._websocket = websocket

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        await self.stop()

    async def stop(self) -> None:
        await self._websocket.close()

    async def _send_message(self, *, content: Dict[str, Any], channel: str, message_type: str) -> str:
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

    async def _receive_message(self, timeout_seconds: Optional[float]) -> Optional[Dict[str, Any]]:
        try:
            if timeout_seconds is not None:
                data = await asyncio.wait_for(self._websocket.recv(), timeout=timeout_seconds)
            else:
                data = await self._websocket.recv()
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            return cast(Dict[str, Any], json.loads(data))
        except asyncio.TimeoutError:
            return None

    async def wait_for_ready(self, timeout_seconds: Optional[float] = None) -> bool:
        message_id = await self._send_message(content={}, channel="shell", message_type="kernel_info_request")
        while True:
            message = await self._receive_message(timeout_seconds)
            # This means we timed out with no new messages.
            if message is None:
                return False
            if (
                message.get("parent_header", {}).get("msg_id") == message_id
                and message["msg_type"] == "kernel_info_reply"
            ):
                return True

    async def execute(self, code: str, timeout_seconds: Optional[float] = None) -> ExecutionResult:
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

        text_output = []
        data_output = []
        while True:
            message = await self._receive_message(timeout_seconds)
            if message is None:
                return JupyterKernelClient.ExecutionResult(
                    is_ok=False, output="ERROR: Timeout waiting for output from code block.", data_items=[]
                )

            # Ignore messages that are not for this execution.
            if message.get("parent_header", {}).get("msg_id") != message_id:
                continue

            msg_type = message["msg_type"]
            content = message["content"]
            if msg_type in ["execute_result", "display_data"]:
                for data_type, data in content["data"].items():
                    if data_type == "text/plain":
                        text_output.append(data)
                    elif data_type.startswith("image/") or data_type == "text/html":
                        data_output.append(self.ExecutionResult.DataItem(mime_type=data_type, data=data))
                    else:
                        text_output.append(json.dumps(data))
            elif msg_type == "stream":
                text_output.append(content["text"])
            elif msg_type == "error":
                # Output is an error.
                return JupyterKernelClient.ExecutionResult(
                    is_ok=False,
                    output=f"ERROR: {content['ename']}: {content['evalue']}\n{content['traceback']}",
                    data_items=[],
                )
            if msg_type == "status" and content["execution_state"] == "idle":
                break
        return JupyterKernelClient.ExecutionResult(
            is_ok=True, output="\n".join([str(output) for output in text_output]), data_items=data_output
        )

class DockerJupyterServer(JupyterConnectable):
    DEFAULT_DOCKERFILE = """FROM quay.io/jupyter/docker-stacks-foundation

        SHELL ["/bin/bash", "-o", "pipefail", "-c"]

        USER ${NB_UID}
        RUN mamba install --yes jupyter_kernel_gateway ipykernel && \
            mamba clean --all -f -y && \
            fix-permissions "${CONDA_DIR}" && \
            fix-permissions "/home/${NB_USER}"

        ENV TOKEN="UNSET"
        CMD python -m jupyter kernelgateway --KernelGatewayApp.ip=0.0.0.0 \
            --KernelGatewayApp.port=8888 \
            --KernelGatewayApp.auth_token="${TOKEN}" \
            --JupyterApp.answer_yes=true \
            --JupyterWebsocketPersonality.list_kernels=true

        EXPOSE 8888

        WORKDIR "${HOME}"
        """

    class GenerateToken:
        pass

    def __init__(
        self,
        *,
        custom_image_name: Optional[str] = None,
        container_name: Optional[str] = None,
        auto_remove: bool = True,
        stop_container: bool = True,
        docker_env: Optional[Dict[str, str]] = None,
        expose_port: int = 8888,
        token: Optional[Union[str, GenerateToken]] = None,
        work_dir: Union[Path, str] = '/workspace',
        bind_dir: Optional[Union[Path, str]] = None,
    ):
        """Start a Jupyter kernel gateway server in a Docker container.

        Args:
            custom_image_name: Custom Docker image to use. If None, builds and uses bundled image.
            container_name: Name for the Docker container. Auto-generated if None.
            auto_remove: If True, container will be deleted when stopped.
            stop_container: If True, container stops on program exit or when context manager exits.
            docker_env: Additional environment variables for the container.
            expose_port: Port to expose for Jupyter connection.
            token: Authentication token. If GenerateToken, creates random token. Empty for no auth.
            work_dir: Working directory inside the container.
            bind_dir: Local directory to bind to container's work_dir.
        """
        # Generate container name if not provided
        container_name = container_name or f"autogen-jupyterkernelgateway-{uuid.uuid4()}"
        
        # Initialize Docker client
        client = docker.from_env()
        # Set up bind directory if specified
        self._bind_dir: Optional[Path] = None
        if bind_dir:
            self._bind_dir = Path(bind_dir) if isinstance(bind_dir, str) else bind_dir
            self._bind_dir.mkdir(exist_ok=True)
            os.chmod(bind_dir, 0o777)
            
        # Determine and prepare Docker image
        image_name = custom_image_name or "autogen-jupyterkernelgateway"
        if not custom_image_name:
            try:
                client.images.get(image_name)
            except docker.errors.ImageNotFound:
                # Build default image if not found
                here = Path(__file__).parent
                dockerfile = io.BytesIO(self.DEFAULT_DOCKERFILE.encode("utf-8"))
                logging.info(f"Building image {image_name}...")
                client.images.build(path=here, fileobj=dockerfile, tag=image_name)
                logging.info(f"Image {image_name} built successfully")
        else:
            # Verify custom image exists
            try:
                client.images.get(image_name)
            except docker.errors.ImageNotFound as err:
                raise ValueError(f"Custom image {image_name} does not exist") from err
        if docker_env is None:
            docker_env = {}
        if token is None:
            token = DockerJupyterServer.GenerateToken()
        # Set up authentication token
        self._token = secrets.token_hex(32) if isinstance(token, DockerJupyterServer.GenerateToken) else token
        
        # Prepare environment variables
        env = {"TOKEN": self._token}
        env.update(docker_env)
        
        # Define volume configuration if bind directory is specified
        volumes = {str(self._bind_dir): {"bind": str(work_dir), "mode": "rw"}} if self._bind_dir else None
        
        # Start the container
        container = client.containers.run(
            image_name,
            detach=True,
            auto_remove=auto_remove,
            environment=env,
            publish_all_ports=True,
            name=container_name,
            volumes=volumes,
            working_dir=str(work_dir),
        )
        
        # Wait for container to be ready
        self._wait_for_ready(container)
        
        # Store container information
        self._container = container
        self._port = int(container.ports[f"{expose_port}/tcp"][0]["HostPort"])
        self._container_id = container.id
        self._expose_port = expose_port
        
        # Define cleanup function
        def cleanup():
            try:
                inner_container = client.containers.get(container.id)
                inner_container.stop()
            except docker.errors.NotFound:
                pass
            atexit.unregister(cleanup)
        
        # Register cleanup if container should be stopped automatically
        if stop_container:
            atexit.register(cleanup)
        
        self._cleanup_func = cleanup
        self._stop_container = stop_container

    @property
    def connection_info(self) -> JupyterConnectionInfo:
        return JupyterConnectionInfo(host="127.0.0.1", use_https=False, port=self._port, token=self._token)

    def _wait_for_ready(self, container: Any, timeout: int = 60, stop_time: float = 0.1) -> None:
        elapsed_time = 0.0
        while container.status != "running" and elapsed_time < timeout:
            sleep(stop_time)
            elapsed_time += stop_time
            container.reload()
            continue
        if container.status != "running":
            raise ValueError("Container failed to start")
    
    async def stop(self) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._cleanup_func)

    async def get_client(self) -> JupyterClient:
        return JupyterClient(self.connection_info)

        
    async def __aenter__(self) -> Self:
        return self
        
    async def __aexit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        await self.stop()
        