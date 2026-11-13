# Distributed Deployment with TLS

This guide explains how to set up AutoGen with full TLS (Transport Layer Security) between all nodes in a distributed environment. This ensures that communication between agents and the host runtime is encrypted and secure.

## Prerequisites

- AutoGen 0.4+ installed.
- `grpcio` and `grpcio-tools` installed (included with `autogen-ext[grpc]`).
- A method to generate or obtain SSL/TLS certificates (e.g., `openssl`).

## Generating Certificates

For development or internal use, you can generate self-signed certificates. For production, you should use certificates from a trusted Certificate Authority (CA).

### Generating Self-Signed Certificates with OpenSSL

```bash
# 1. Generate a CA private key and self-signed certificate
openssl req -x509 -newkey rsa:4096 -keyout ca-key.pem -out ca-cert.pem -days 365 -nodes -subj "/CN=MyAutoGenCA"

# 2. Generate a server private key and CSR
openssl req -newkey rsa:4096 -keyout server-key.pem -out server-csr.pem -nodes -subj "/CN=localhost"

# 3. Sign the server CSR with the CA certificate
openssl x509 -req -in server-csr.pem -CA ca-cert.pem -CAkey ca-key.pem -CAcreateserial -out server-cert.pem -days 365
```

## Configuring the Host Runtime

The `GrpcWorkerAgentRuntimeHost` now accepts `server_credentials`.

```python
import grpc
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntimeHost

# Load certificates
with open("server-key.pem", "rb") as f:
    private_key = f.read()
with open("server-cert.pem", "rb") as f:
    certificate_chain = f.read()

# Create server credentials
server_credentials = grpc.ssl_server_credentials(
    [(private_key, certificate_chain)]
)

# Start the host with TLS
host = GrpcWorkerAgentRuntimeHost(
    address="localhost:50051",
    server_credentials=server_credentials
)
host.start()
```

## Configuring Worker Runtimes

The `GrpcWorkerAgentRuntime` now accepts `channel_credentials`.

```python
import grpc
from autogen_ext.runtimes.grpc import GrpcWorkerAgentRuntime

# Load CA certificate
with open("ca-cert.pem", "rb") as f:
    ca_cert = f.read()

# Create channel credentials
channel_credentials = grpc.ssl_channel_credentials(root_certificates=ca_cert)

# Start the worker with TLS
worker = GrpcWorkerAgentRuntime(
    host_address="localhost:50051",
    channel_credentials=channel_credentials
)
await worker.start()
```

## .NET Implementation

For .NET developers, TLS support is provided through the standard ASP.NET Core gRPC infrastructure. To enable TLS:

1.  **Configure Kestrel**: Set up your host to use HTTPS via `appsettings.json` or `WebApplication.CreateBuilder`.
2.  **Use HTTPS Addresses**: When connecting workers, use the `https://` protocol in the agent service address.
3.  **Certificate Validation**: If using self-signed certificates, configure the `HttpClient` used by the gRPC client to trust your CA or bypass validation for development.

## Production Considerations

- **Certificate Management**: Use services like Azure Key Vault, AWS Secrets Manager, or HashiCorp Vault to store and automate certificate rotation.
- **Mutual TLS (mTLS)**: For even higher security, you can configure mTLS where the server also verifies the client's certificate. This is supported by gRPC by providing `root_certificates` to the server and `private_key`/`certificate_chain` to the client.
- **Environment Variables**: Avoid hardcoding paths or certificate content. Use environment variables to pass certificate data or paths to your application.
