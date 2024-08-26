# Copyright (c) 2023 - 2024, Owners of https://github.com/autogen-ai
#
# SPDX-License-Identifier: Apache-2.0
#
# Original portions of this file are derived from https://github.com/microsoft/autogen under the MIT License.
# SPDX-License-Identifier: MIT
from __future__ import annotations

import atexit
import io
import logging
import secrets
import sys
import uuid
from pathlib import Path
from types import TracebackType
from typing import Dict, Optional, Type, Union

import docker

from ..docker_commandline_code_executor import _wait_for_ready

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


from .base import JupyterConnectable, JupyterConnectionInfo
from .jupyter_client import JupyterClient


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
        docker_env: Dict[str, str] = {},
        token: Union[str, GenerateToken] = GenerateToken(),
    ):
        """Start a Jupyter kernel gateway server in a Docker container.

        Args:
            custom_image_name (Optional[str], optional): Custom image to use. If this is None,
                then the bundled image will be built and used. The default image is based on
                quay.io/jupyter/docker-stacks-foundation and extended to include jupyter_kernel_gateway
            container_name (Optional[str], optional): Name of the container to start.
                A name will be generated if None.
            auto_remove (bool, optional): If true the Docker container will be deleted
                when it is stopped.
            stop_container (bool, optional): If true the container will be stopped,
                either by program exit or using the context manager
            docker_env (Dict[str, str], optional): Extra environment variables to pass
                to the running Docker container.
            token (Union[str, GenerateToken], optional): Token to use for authentication.
                If GenerateToken is used, a random token will be generated. Empty string
                will be unauthenticated.
        """
        if container_name is None:
            container_name = f"autogen-jupyterkernelgateway-{uuid.uuid4()}"

        client = docker.from_env()
        if custom_image_name is None:
            image_name = "autogen-jupyterkernelgateway"
            # Make sure the image exists
            try:
                client.images.get(image_name)
            except docker.errors.ImageNotFound:
                # Build the image
                # Get this script directory
                here = Path(__file__).parent
                dockerfile = io.BytesIO(self.DEFAULT_DOCKERFILE.encode("utf-8"))
                logging.info(f"Image {image_name} not found. Building it now.")
                client.images.build(path=here, fileobj=dockerfile, tag=image_name)
                logging.info(f"Image {image_name} built successfully.")
        else:
            image_name = custom_image_name
            # Check if the image exists
            try:
                client.images.get(image_name)
            except docker.errors.ImageNotFound:
                raise ValueError(f"Custom image {image_name} does not exist")

        if isinstance(token, DockerJupyterServer.GenerateToken):
            self._token = secrets.token_hex(32)
        else:
            self._token = token

        # Run the container
        env = {"TOKEN": self._token}
        env.update(docker_env)
        container = client.containers.run(
            image_name,
            detach=True,
            auto_remove=auto_remove,
            environment=env,
            publish_all_ports=True,
            name=container_name,
        )
        _wait_for_ready(container)
        container_ports = container.ports
        self._port = int(container_ports["8888/tcp"][0]["HostPort"])
        self._container_id = container.id

        def cleanup() -> None:
            try:
                inner_container = client.containers.get(container.id)
                inner_container.stop()
            except docker.errors.NotFound:
                pass

            atexit.unregister(cleanup)

        if stop_container:
            atexit.register(cleanup)

        self._cleanup_func = cleanup
        self._stop_container = stop_container

    @property
    def connection_info(self) -> JupyterConnectionInfo:
        return JupyterConnectionInfo(host="127.0.0.1", use_https=False, port=self._port, token=self._token)

    def stop(self) -> None:
        self._cleanup_func()

    def get_client(self) -> JupyterClient:
        return JupyterClient(self.connection_info)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[TracebackType]
    ) -> None:
        self.stop()
