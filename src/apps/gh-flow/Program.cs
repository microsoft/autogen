using System.Text.Json;
using Microsoft.AI.DevTeam;
using Microsoft.Extensions.Options;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.AI.OpenAI.TextEmbedding;
using Microsoft.SemanticKernel.Connectors.Memory.Qdrant;
using Microsoft.SemanticKernel.Memory;
using Microsoft.SemanticKernel.Reliability.Basic;
using Octokit.Webhooks;
using Octokit.Webhooks.AspNetCore;
using Orleans.Configuration;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddSingleton<WebhookEventProcessor, GithubWebHookProcessor>();
builder.Services.AddTransient(CreateKernel);
builder.Services.AddHttpClient();

builder.Services.AddSingleton(s =>
{
    var ghOptions = s.GetService<IOptions<GithubOptions>>();
    var logger = s.GetService<ILogger<GithubAuthService>>();
    var ghService = new GithubAuthService(ghOptions, logger);
    var client = ghService.GetGitHubClient().Result;
    return client;
});
builder.Services.AddSingleton<GithubAuthService>();

builder.Services.AddApplicationInsightsTelemetry();
builder.Services.AddOptions<GithubOptions>()
    .Configure<IConfiguration>((settings, configuration) =>
    {
        configuration.GetSection("GithubOptions").Bind(settings);
    });
builder.Services.AddOptions<AzureOptions>()
    .Configure<IConfiguration>((settings, configuration) =>
    {
        configuration.GetSection("AzureOptions").Bind(settings);
    });
builder.Services.AddOptions<OpenAIOptions>()
    .Configure<IConfiguration>((settings, configuration) =>
    {
        configuration.GetSection("OpenAIOptions").Bind(settings);
    });
builder.Services.AddOptions<QdrantOptions>()
    .Configure<IConfiguration>((settings, configuration) =>
    {
        configuration.GetSection("QdrantOptions").Bind(settings);
    });
builder.Services.AddOptions<ServiceOptions>()
    .Configure<IConfiguration>((settings, configuration) =>
    {
        configuration.GetSection("ServiceOptions").Bind(settings);
    });

builder.Services.AddSingleton<IManageAzure, AzureService>();
builder.Services.AddSingleton<IManageGithub, GithubService>();
builder.Services.AddSingleton<IAnalyzeCode, CodeAnalyzer>();


builder.Host.UseOrleans(siloBuilder =>
{
    
    if (builder.Environment.IsDevelopment())
    {
        var connectionString = builder.Configuration.GetValue<string>("AzureOptions:CosmosConnectionString");
        siloBuilder.UseCosmosReminderService( o => 
        {
                o.ConfigureCosmosClient(connectionString);
                o.ContainerName = "reminders";
                o.DatabaseName = "devteam";
                o.IsResourceCreationEnabled = true;
        });
        siloBuilder.AddCosmosGrainStorage(
            name: "messages",
            configureOptions: o =>
            {
                o.ConfigureCosmosClient(connectionString);
                o.ContainerName = "persistence";
                o.DatabaseName = "devteam";
                o.IsResourceCreationEnabled = true;
            });
        siloBuilder.UseLocalhostClustering();
    }
    else
    {
        var cosmosDbconnectionString = builder.Configuration.GetValue<string>("AzureOptions:CosmosConnectionString");
        siloBuilder.Configure<ClusterOptions>(options =>
        {
            options.ClusterId = "ai-dev-cluster";
            options.ServiceId = "ai-dev-cluster";
        });
        siloBuilder.Configure<SiloMessagingOptions>(options =>
        {
            options.ResponseTimeout = TimeSpan.FromMinutes(3);
            options.SystemResponseTimeout = TimeSpan.FromMinutes(3);
        });
         siloBuilder.Configure<ClientMessagingOptions>(options =>
        {
            options.ResponseTimeout = TimeSpan.FromMinutes(3);
        });
        siloBuilder.UseCosmosClustering( o =>
            {
                o.ConfigureCosmosClient(cosmosDbconnectionString);
                o.ContainerName = "devteam";
                o.DatabaseName = "clustering";
                o.IsResourceCreationEnabled = true;
            });
        
        siloBuilder.UseCosmosReminderService( o => 
        {
                o.ConfigureCosmosClient(cosmosDbconnectionString);
                o.ContainerName = "devteam";
                o.DatabaseName = "reminders";
                o.IsResourceCreationEnabled = true;
        });
        siloBuilder.AddCosmosGrainStorage(
            name: "messages",
            configureOptions: o =>
            {
                o.ConfigureCosmosClient(cosmosDbconnectionString);
                o.ContainerName = "devteam";
                o.DatabaseName = "persistence";
                o.IsResourceCreationEnabled = true;
            });
    }    
   
});

builder.Services.Configure<JsonSerializerOptions>(options =>
{
    options.PropertyNamingPolicy = JsonNamingPolicy.CamelCase;
});
var app = builder.Build();

app.UseRouting();

app.UseEndpoints(endpoints =>
{
    endpoints.MapGitHubWebhooks();
});


app.Run();

static IKernel CreateKernel(IServiceProvider provider)
{
    var openAiConfig = provider.GetService<IOptions<OpenAIOptions>>().Value;
    var qdrantConfig = provider.GetService<IOptions<QdrantOptions>>().Value;

    var loggerFactory = LoggerFactory.Create(builder =>
    {
        builder
            .SetMinimumLevel(LogLevel.Debug)
            .AddConsole()
            .AddDebug();
    });

    var memoryStore = new QdrantMemoryStore(new QdrantVectorDbClient(qdrantConfig.Endpoint, qdrantConfig.VectorSize));
    var embedingGeneration = new AzureTextEmbeddingGeneration(openAiConfig.EmbeddingDeploymentOrModelId, openAiConfig.Endpoint, openAiConfig.ApiKey);
    var semanticTextMemory = new SemanticTextMemory(memoryStore, embedingGeneration);

    return new KernelBuilder()
                        .WithLoggerFactory(loggerFactory)
                        .WithAzureChatCompletionService(openAiConfig.DeploymentOrModelId, openAiConfig.Endpoint, openAiConfig.ApiKey, true, openAiConfig.ServiceId, true)
                        .WithRetryBasic(new BasicRetryConfig {
                            MaxRetryCount = 5,
                            UseExponentialBackoff = true
                        })
                        .WithMemory(semanticTextMemory).Build();
}