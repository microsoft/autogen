// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Microsoft.Extensions.Hosting;

var builder = DistributedApplication.CreateBuilder(args);
var backend = builder.AddProject<Projects.Backend>("backend").WithExternalHttpEndpoints();
builder.AddProject<Projects.HelloAgent>("client")
    .WithReference(backend)
    .WithEnvironment("AGENT_HOST", $"{backend.GetEndpoint("https").Property(EndpointProperty.Url)}")
    .WithEnvironment("STAY_ALIVE_ON_GOODBYE", "true")
    .WaitFor(backend);
#pragma warning disable ASPIREHOSTINGPYTHON001 // Type is for evaluation purposes only and is subject to change or removal in future updates. Suppress this diagnostic to proceed.
builder.AddPythonApp("hello-python", "../HelloPythonAgent", "hello_python_agent.py", "../../../../python/.venv")
    .WithReference(backend)
    .WithEnvironment("AGENT_HOST", "backend-http")
    .WithEnvironment("STAY_ALIVE_ON_GOODBYE", "true")
    .WithEnvironment("GRPC_DNS_RESOLVER", "native")
    .WithOtlpExporter()
    .WaitFor(backend);
#pragma warning restore ASPIREHOSTINGPYTHON001 // Type is for evaluation purposes only and is subject to change or removal in future updates. Suppress this diagnostic to proceed.
using var app = builder.Build();
await app.StartAsync();
var url = backend.GetEndpoint("http").Url;
Console.WriteLine("Backend URL: " + url);
await app.WaitForShutdownAsync();
