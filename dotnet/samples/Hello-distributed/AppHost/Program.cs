// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

var builder = DistributedApplication.CreateBuilder(args);

var agentHost = builder.AddContainer("agent-host", "autogen-host")
                       .WithEnvironment("ASPNETCORE_URLS", "http://+:5001")
                       .WithHttpEndpoint(port:5001, targetPort: 5001);

var agentHostHttp = agentHost.GetEndpoint("http");
var url = agentHostHttp.Property(EndpointProperty.Url);

builder.AddProject<Projects.Backend>("backend")
    .WithEnvironment("AGENT_HOST", $"{url}")
    .WithEnvironment("OpenAI__Key", builder.Configuration["OpenAI:Key"])
    .WithEnvironment("OpenAI__Endpoint", builder.Configuration["OpenAI:Endpoint"])
    .WaitFor(agentHost);

builder.Build().Run();
