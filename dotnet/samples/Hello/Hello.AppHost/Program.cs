// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Microsoft.Extensions.Hosting;

var builder = DistributedApplication.CreateBuilder(args);

var agentHost = builder.AddContainer("agent-host", "autogen-host")
                       .WithEnvironment("ASPNETCORE_URLS", "https://+;http://+")
                       .WithEnvironment("ASPNETCORE_HTTPS_PORTS", "5001")
                       .WithEnvironment("ASPNETCORE_Kestrel__Certificates__Default__Password", "mysecurepass")
                       .WithEnvironment("ASPNETCORE_Kestrel__Certificates__Default__Path", "/https/devcert.pfx")
                       .WithBindMount("./certs", "/https/", true)
                       .WithHttpsEndpoint(targetPort: 5001);

var agentHostHttps = agentHost.GetEndpoint("https");

builder.AddProject<Projects.HelloAgent>("client")
    .WithEnvironment("AGENT_HOST", $"{agentHostHttps.Property(EndpointProperty.Url)}")
    .WaitFor(agentHost);

using var app = builder.Build();

await app.StartAsync();

await app.WaitForShutdownAsync();
