// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

var builder = DistributedApplication.CreateBuilder(args);

builder.AddAzureProvisioning();

var orleans = builder.AddOrleans("orleans")
    .WithDevelopmentClustering();

var agentHost = builder.AddProject<Projects.Marketing_AgentHost>("agenthost")
    .WithReference(orleans);
var agentHostHttps = agentHost.GetEndpoint("https");

var backend = builder.AddProject<Projects.Marketing_Backend>("backend")
    .WithEnvironment("AGENT_HOST", $"{agentHostHttps.Property(EndpointProperty.Url)}")
    .WithEnvironment("OpenAI__Key", builder.Configuration["OpenAI:Key"])
    .WithEnvironment("OpenAI__Endpoint", builder.Configuration["OpenAI:Endpoint"]);

builder.AddProject<Projects.Marketing_Agents>("marketing-agents")
    .WithEnvironment("AGENT_HOST", $"{agentHostHttps.Property(EndpointProperty.Url)}")
    .WithEnvironment("OpenAI__Key", builder.Configuration["OpenAI:Key"])
    .WithEnvironment("OpenAI__Endpoint", builder.Configuration["OpenAI:Endpoint"]);

//var ep = agentHost.GetEndpoint("http");

//builder.AddPythonProject("python-worker", "../../../../../python/", "./packages/autogen-core/samples/marketing-team/worker.py")
//        .WithEnvironment("AGENT_HOST", $"{agentHostHttps.Property(EndpointProperty.Host)}:{agentHostHttps.Property(EndpointProperty.Port)}");

builder.AddNpmApp("frontend", "../Marketing.Frontend", "dev")
    .WithReference(backend)
    .WithEnvironment("NEXT_PUBLIC_BACKEND_URI", backend.GetEndpoint("http"))
    .WithHttpEndpoint(env: "PORT")
    .WithExternalHttpEndpoints()
    .PublishAsDockerFile();

builder.Build().Run();
