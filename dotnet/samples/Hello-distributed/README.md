# Hello world sample using the packaged agent host

To run this sample, we'll need to generate self-signed certificate, as the gRPC server on the agenthost is configured to use HTTPS.

Run the following commands from `\dotnet\samples\Hello-distributed\AppHost`

```bash
mkdir certs
dotnet dev-certs https -ep ./certs/devcert.pfx -p mysecurepass
dotnet dev-certs https --trust
```