// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

var builder = DistributedApplication.CreateBuilder(args);

var agentHost = builder.AddContainer("agent-host", "autogen-host")
                       .WithEnvironment("ASPNETCORE_URLS", "https://+;http://+")
                       .WithEnvironment("ASPNETCORE_HTTPS_PORTS", "5001")
                       .WithEnvironment("ASPNETCORE_Kestrel__Certificates__Default__Password", "mysecurepass")
                       .WithEnvironment("ASPNETCORE_Kestrel__Certificates__Default__Path", "/https/devcert.pfx")
                       .WithBindMount("./certs", "/https/", true)
                       .WithHttpsEndpoint(targetPort: 5001);

var client = builder.AddProject<Projects.HelloAgent>("HelloAgentsDotNET")
    .WithEnvironment("AGENT_HOST", agentHost.GetEndpoint("https"))
    .WithEnvironment("STAY_ALIVE_ON_GOODBYE", "true")
    .WaitFor(agentHost);

#pragma warning disable ASPIREHOSTINGPYTHON001 // Type is for evaluation purposes only and is subject to change or removal in future updates. Suppress this diagnostic to proceed.
// xlang is over http for now - in prod use TLS between containers
builder.AddPythonApp("HelloAgentsPython", "../../../../python/packages/autogen-core/samples/xlang/hello_python_agent", "hello_python_agent.py", "../../../../../.venv")
    .WithEnvironment("AGENT_HOST", agentHost.GetEndpoint("http"))
    .WithEnvironment("STAY_ALIVE_ON_GOODBYE", "true")
    .WithEnvironment("GRPC_DNS_RESOLVER", "native")
    .WithOtlpExporter()
    .WaitFor(client);
#pragma warning restore ASPIREHOSTINGPYTHON001 // Type is for evaluation purposes only and is subject to change or removal in future updates. Suppress this diagnostic to proceed.
builder.Build().Run();
