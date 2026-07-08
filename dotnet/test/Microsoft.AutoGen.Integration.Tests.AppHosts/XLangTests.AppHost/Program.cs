// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs
using Aspire.Hosting.Python;
using Microsoft.Extensions.Hosting;
const string pythonHelloAgentPath = "../core_xlang_hello_python_agent";
const string pythonHelloAgentPy = "hello_python_agent.py";
const string pythonVEnv = "../../../../python/.venv";
//Environment.SetEnvironmentVariable("XLANG_TEST_NO_DOTNET", "true");
//Environment.SetEnvironmentVariable("XLANG_TEST_NO_PYTHON", "true");
var builder = DistributedApplication.CreateBuilder(args);
var backend = builder.AddProject<Projects.Microsoft_AutoGen_AgentHost>("AgentHost").WithExternalHttpEndpoints();
IResourceBuilder<ProjectResource>? dotnet = null;
#pragma warning disable ASPIREHOSTINGPYTHON001 // Type is for evaluation purposes only and is subject to change or removal in future updates. Suppress this diagnostic to proceed.
IResourceBuilder<PythonAppResource>? python = null;
if (string.IsNullOrEmpty(Environment.GetEnvironmentVariable("XLANG_TEST_NO_DOTNET")))
{
    dotnet = builder.AddProject<Projects.HelloAgentTests>("HelloAgentTestsDotNET")
        .WithReference(backend)
        .WithEnvironment("AGENT_HOST", backend.GetEndpoint("https"))
        .WithEnvironment("STAY_ALIVE_ON_GOODBYE", "true")
        .WaitFor(backend);
}
if (string.IsNullOrEmpty(Environment.GetEnvironmentVariable("XLANG_TEST_NO_PYTHON")))
{
    // xlang is over http for now - in prod use TLS between containers
    python = builder.AddPythonApp("HelloAgentTestsPython", pythonHelloAgentPath, pythonHelloAgentPy, pythonVEnv)
        .WithReference(backend)
        .WithEnvironment("AGENT_HOST", backend.GetEndpoint("http"))
        .WithEnvironment("STAY_ALIVE_ON_GOODBYE", "true")
        .WithEnvironment("GRPC_DNS_RESOLVER", "native")
        .WithOtlpExporter()
        .WaitFor(backend);
    if (dotnet != null) { python.WaitFor(dotnet); }
}
#pragma warning restore ASPIREHOSTINGPYTHON001 // Type is for evaluation purposes only and is subject to change or removal in future updates. Suppress this diagnostic to proceed.
using var app = builder.Build();
await app.StartAsync();
var url = backend.GetEndpoint("http").Url;
Console.WriteLine("Backend URL: " + url);
if (dotnet != null) { Console.WriteLine("Dotnet Resource Projects.HelloAgentTests invoked as HelloAgentTestsDotNET"); }
if (python != null) { Console.WriteLine("Python Resource hello_python_agent.py invoked as HelloAgentTestsPython"); }
await app.WaitForShutdownAsync();
