// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Microsoft.Extensions.Hosting;

var builder = DistributedApplication.CreateBuilder(args);
var backend = builder.AddProject<Projects.Microsoft_AutoGen_AgentHost>("backend").WithExternalHttpEndpoints();
var client = builder.AddProject<Projects.HelloAgent>("HelloAgentsDotNET")
    .WithReference(backend)
    .WithEnvironment("AGENT_HOST", backend.GetEndpoint("https"))
    .WithEnvironment("STAY_ALIVE_ON_GOODBYE", "true")
    .WaitFor(backend);
#pragma warning disable ASPIREHOSTINGPYTHON001 // Type is for evaluation purposes only and is subject to change or removal in future updates. Suppress this diagnostic to proceed.
// xlang is over http for now - in prod use TLS between containers
builder.AddPythonApp("HelloAgentsPython", "../../../../python/samples/core_xlang_hello_python_agent", "hello_python_agent.py", "../../.venv")
    .WithReference(backend)
    .WithEnvironment("AGENT_HOST", backend.GetEndpoint("http"))
    .WithEnvironment("STAY_ALIVE_ON_GOODBYE", "true")
    .WithEnvironment("GRPC_DNS_RESOLVER", "native")
    .WithOtlpExporter()
    .WaitFor(client);
#pragma warning restore ASPIREHOSTINGPYTHON001 // Type is for evaluation purposes only and is subject to change or removal in future updates. Suppress this diagnostic to proceed.
using var app = builder.Build();
await app.StartAsync();
var url = backend.GetEndpoint("http").Url;
Console.WriteLine("Backend URL: " + url);
await app.WaitForShutdownAsync();
