import asyncio
import logging
import os
import subprocess
import tempfile
from typing import Any, List

import grpc
import pytest
from autogen_core import (
    AgentId,
    AgentType,
    DefaultTopicId,
)
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntime, GrpcWorkerAgentRuntimeHost
from autogen_test_utils import (
    LoopbackAgent,
    MessageType,
    NoopAgent,
)

def generate_certs(cert_dir: str):
    ca_key = os.path.join(cert_dir, "ca-key.pem")
    ca_cert = os.path.join(cert_dir, "ca-cert.pem")
    server_key = os.path.join(cert_dir, "server-key.pem")
    server_csr = os.path.join(cert_dir, "server-csr.pem")
    server_cert = os.path.join(cert_dir, "server-cert.pem")

    # 1. Generate a CA private key and self-signed certificate
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-keyout", ca_key, "-out", ca_cert, "-days", "1", "-nodes", "-subj", "/CN=TestCA"], check=True)

    # 2. Generate a server private key and CSR
    subprocess.run(["openssl", "req", "-newkey", "rsa:2048", "-keyout", server_key, "-out", server_csr, "-nodes", "-subj", "/CN=localhost"], check=True)

    # 3. Sign the server CSR with the CA certificate
    subprocess.run(["openssl", "x509", "-req", "-in", server_csr, "-CA", ca_cert, "-CAkey", ca_key, "-CAcreateserial", "-out", server_cert, "-days", "1"], check=True)

    return ca_cert, server_key, server_cert

from autogen_core import try_get_known_serializers_for_type
from autogen_test_utils import ContentMessage

@pytest.mark.grpc
@pytest.mark.asyncio
async def test_tls_communication() -> None:
    with tempfile.TemporaryDirectory() as cert_dir:
        ca_cert_path, server_key_path, server_cert_path = generate_certs(cert_dir)

        with open(server_key_path, "rb") as f:
            private_key = f.read()
        with open(server_cert_path, "rb") as f:
            certificate_chain = f.read()
        with open(ca_cert_path, "rb") as f:
            root_certs = f.read()

        server_credentials = grpc.ssl_server_credentials([(private_key, certificate_chain)])
        channel_credentials = grpc.ssl_channel_credentials(root_certificates=root_certs)

        host_address = "localhost:50062"
        host = GrpcWorkerAgentRuntimeHost(address=host_address, server_credentials=server_credentials)
        host.start()

        worker = GrpcWorkerAgentRuntime(host_address=host_address, channel_credentials=channel_credentials)
        worker.add_message_serializer(try_get_known_serializers_for_type(ContentMessage))
        await worker.start()

        await worker.register_factory(type=AgentType("loopback"), agent_factory=lambda: LoopbackAgent(), expected_class=LoopbackAgent)
        
        # Test basic messaging
        recipient = AgentId("loopback", "default")
        response = await worker.send_message(ContentMessage(content="Hello TLS!"), recipient=recipient)
        assert response == ContentMessage(content="Hello TLS!")

        await worker.stop()
        await host.stop()

@pytest.mark.grpc
@pytest.mark.asyncio
async def test_tls_invalid_credentials() -> None:
    with tempfile.TemporaryDirectory() as cert_dir:
        ca_cert_path, server_key_path, server_cert_path = generate_certs(cert_dir)
        
        # Generate ANOTHER CA that is not trusted
        other_ca_cert = os.path.join(cert_dir, "other-ca-cert.pem")
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-keyout", os.path.join(cert_dir, "other-ca-key.pem"), "-out", other_ca_cert, "-days", "1", "-nodes", "-subj", "/CN=OtherCA"], check=True)

        with open(server_key_path, "rb") as f:
            private_key = f.read()
        with open(server_cert_path, "rb") as f:
            certificate_chain = f.read()
        with open(other_ca_cert, "rb") as f:
            wrong_root_certs = f.read()

        server_credentials = grpc.ssl_server_credentials([(private_key, certificate_chain)])
        channel_credentials = grpc.ssl_channel_credentials(root_certificates=wrong_root_certs)

        host_address = "localhost:50063"
        host = GrpcWorkerAgentRuntimeHost(address=host_address, server_credentials=server_credentials)
        host.start()

        worker = GrpcWorkerAgentRuntime(host_address=host_address, channel_credentials=channel_credentials)
        
        # This should fail to connect or time out
        with pytest.raises(Exception):
             await asyncio.wait_for(worker.start(), timeout=5)

        await host.stop()
