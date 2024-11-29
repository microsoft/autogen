// Copyright (c) Microsoft Corporation. All rights reserved.
// Program.cs

var builder = DistributedApplication.CreateBuilder(args);

builder.AddAzureProvisioning();

var qdrant = builder.AddQdrant("qdrant");

var agentHost = builder.AddContainer("agent-host", "autogen-host")
                       .WithEnvironment("ASPNETCORE_URLS", "https://+;http://+")
                       .WithEnvironment("ASPNETCORE_HTTPS_PORTS", "5001")
                       .WithEnvironment("ASPNETCORE_Kestrel__Certificates__Default__Password", "mysecurepass")
                       .WithEnvironment("ASPNETCORE_Kestrel__Certificates__Default__Path", "/https/devcert.pfx")
                       .WithBindMount("./certs", "/https/", true)
                       .WithHttpsEndpoint(targetPort: 5001);

var agentHostHttps = agentHost.GetEndpoint("https");

//TODO: pass the right variables - aca environment
// var environmentId = builder.AddParameter("environmentId");
// var acaSessions = builder.AddBicepTemplateString(
//         name: "aca-sessions",
//         bicepContent: BicepTemplates.Sessions
//     )
//     .WithParameter("environmentId", environmentId);
// var acaSessionsEndpoint = acaSessions.GetOutput("endpoint");

builder.AddProject<Projects.DevTeam_Backend>("backend")
    .WithEnvironment("AGENT_HOST", $"{agentHostHttps.Property(EndpointProperty.Url)}")
    .WithEnvironment("Qdrant__Endpoint", $"{qdrant.Resource.HttpEndpoint.Property(EndpointProperty.Url)}")
    .WithEnvironment("Qdrant__ApiKey", $"{qdrant.Resource.ApiKeyParameter.Value}")
    .WithEnvironment("Qdrant__VectorSize", "1536")
    .WithEnvironment("OpenAI__Key", builder.Configuration["OpenAI:Key"])
    .WithEnvironment("OpenAI__Endpoint", builder.Configuration["OpenAI:Endpoint"])
    .WithEnvironment("Github__AppId", builder.Configuration["Github:AppId"])
    .WithEnvironment("Github__InstallationId", builder.Configuration["Github:InstallationId"])
    .WithEnvironment("Github__WebhookSecret", builder.Configuration["Github:WebhookSecret"])
    .WithEnvironment("Github__AppKey", builder.Configuration["Github:AppKey"]);
//TODO: add this to the config in backend
//.WithEnvironment("", acaSessionsEndpoint);

builder.AddProject<Projects.DevTeam_Agents>("dev-agents")
    .WithEnvironment("AGENT_HOST", $"{agentHostHttps.Property(EndpointProperty.Url)}")
    .WithEnvironment("Qdrant__Endpoint", $"{qdrant.Resource.HttpEndpoint.Property(EndpointProperty.Url)}")
    .WithEnvironment("Qdrant__ApiKey", $"{qdrant.Resource.ApiKeyParameter.Value}")
    .WithEnvironment("Qdrant__VectorSize", "1536")
    .WithEnvironment("OpenAI__Key", builder.Configuration["OpenAI:Key"])
    .WithEnvironment("OpenAI__Endpoint", builder.Configuration["OpenAI:Endpoint"]);

builder.Build().Run();
