// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

using Microsoft.Extensions.Hosting;

var builder = DistributedApplication.CreateBuilder(args);
var backend = builder.AddProject<Projects.Backend>("backend").WithExternalHttpEndpoints();
builder.AddProject<Projects.HelloAgent>("client")
    .WithReference(backend)
    .WithEnvironment("AGENT_HOST", $"{backend.GetEndpoint("https").Property(EndpointProperty.Url)}")
    .WaitFor(backend);

using var app = builder.Build();

await app.StartAsync();
var url = backend.GetEndpoint("http").Url;
Console.WriteLine("Backend URL: " + url);

await app.WaitForShutdownAsync();
