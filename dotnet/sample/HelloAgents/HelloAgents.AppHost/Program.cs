var builder = DistributedApplication.CreateBuilder(args);

var apiService = builder.AddProject<Projects.HelloAgents_ApiService>("apiservice");

builder.AddProject<Projects.HelloAgents_Web>("webfrontend")
    .WithExternalHttpEndpoints()
    .WithReference(apiService);

builder.Build().Run();
