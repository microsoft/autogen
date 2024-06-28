var builder = DistributedApplication.CreateBuilder(args);

builder.AddAzureProvisioning();

var orleans = builder.AddOrleans("orleans")
    .WithDevelopmentClustering()
    .WithMemoryReminders()
    .WithMemoryGrainStorage("agent-state");

var agentHost = builder.AddProject<Projects.Greeter_AgentHost>("agenthost")
    .WithReference(orleans);

builder.AddProject<Projects.Greeter_AgentWorker>("csharp-worker")
    .WithExternalHttpEndpoints()
    .WithReference(agentHost);

var ep = agentHost.GetEndpoint("http");
builder.AddExecutable("python-worker", "hatch", "../../../../python/", "run", "python", "worker_example.py")
        .WithEnvironment("AGENT_HOST", $"{ep.Property(EndpointProperty.Host)}:{ep.Property(EndpointProperty.Port)}");

builder.Build().Run();
