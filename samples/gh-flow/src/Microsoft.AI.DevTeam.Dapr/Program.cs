using System.Text.Json;
using Azure;
using Azure.AI.OpenAI;
using Microsoft.Extensions.Options;
using Microsoft.SemanticKernel;
using Octokit.Webhooks;
using Octokit.Webhooks.AspNetCore;
using Azure.Identity;
using Microsoft.Extensions.Azure;
using Microsoft.Extensions.Http.Resilience;
using Microsoft.SemanticKernel.Memory;
using Microsoft.SemanticKernel.Connectors.Qdrant;
using Microsoft.SemanticKernel.Connectors.OpenAI;
using Dapr;
using Dapr.Actors.Client;
using Dapr.Actors;
using Microsoft.AI.DevTeam.Dapr;
using Microsoft.AI.DevTeam.Dapr.Events;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddSingleton<WebhookEventProcessor, GithubWebHookProcessor>();
builder.Services.AddTransient(CreateKernel);
builder.Services.AddTransient(CreateMemory);
builder.Services.AddHttpClient();

builder.Services.AddSingleton(s =>
{
    var ghOptions = s.GetService<IOptions<GithubOptions>>();
    var logger = s.GetService<ILogger<GithubAuthService>>();
    var ghService = new GithubAuthService(ghOptions, logger);
    var client = ghService.GetGitHubClient();
    return client;
});


builder.Services.AddAzureClients(clientBuilder =>
{
    clientBuilder.UseCredential(new DefaultAzureCredential());
    clientBuilder.AddArmClient(default);
});

builder.Services.AddDaprClient();

builder.Services.AddActors(
    options =>
    {
        options.UseJsonSerialization = true;
        options.JsonSerializerOptions = new JsonSerializerOptions(JsonSerializerDefaults.Web);
        options.ReentrancyConfig = new ActorReentrancyConfig {
            Enabled = true
        };
        options.Actors.RegisterActor<Dev>();
        options.Actors.RegisterActor<DeveloperLead>();
        options.Actors.RegisterActor<ProductManager>();
        options.Actors.RegisterActor<AzureGenie>();
        options.Actors.RegisterActor<Hubber>();
        options.Actors.RegisterActor<Sandbox>();
    });

builder.Services.AddSingleton<GithubAuthService>();

builder.Services.AddApplicationInsightsTelemetry();
builder.Services.AddOptions<GithubOptions>()
    .Configure<IConfiguration>((settings, configuration) =>
    {
        configuration.GetSection(nameof(GithubOptions)).Bind(settings);
    })
    .ValidateDataAnnotations()
    .ValidateOnStart();

builder.Services.AddOptions<AzureOptions>()
    .Configure<IConfiguration>((settings, configuration) =>
    {
        configuration.GetSection(nameof(AzureOptions)).Bind(settings);
    })
    .ValidateDataAnnotations()
    .ValidateOnStart();

builder.Services.AddOptions<OpenAIOptions>()
    .Configure<IConfiguration>((settings, configuration) =>
    {
        configuration.GetSection(nameof(OpenAIOptions)).Bind(settings);
    })
    .ValidateDataAnnotations()
    .ValidateOnStart();

builder.Services.AddOptions<QdrantOptions>()
    .Configure<IConfiguration>((settings, configuration) =>
    {
        configuration.GetSection(nameof(QdrantOptions)).Bind(settings);
    })
    .ValidateDataAnnotations()
    .ValidateOnStart();

builder.Services.AddOptions<ServiceOptions>()
    .Configure<IConfiguration>((settings, configuration) =>
    {
        configuration.GetSection(nameof(ServiceOptions)).Bind(settings);
    })
    .ValidateDataAnnotations()
    .ValidateOnStart();

builder.Services.AddSingleton<IManageAzure, AzureService>();
builder.Services.AddSingleton<IManageGithub, GithubService>();
builder.Services.AddSingleton<IAnalyzeCode, CodeAnalyzer>();


builder.Services.Configure<JsonSerializerOptions>(options =>
{
    options.PropertyNamingPolicy = JsonNamingPolicy.CamelCase;
});
var app = builder.Build();

app.UseRouting()
   .UseEndpoints(endpoints =>
{
    var ghOptions = app.Services.GetService<IOptions<GithubOptions>>().Value;
    endpoints.MapGitHubWebhooks(secret: ghOptions.WebhookSecret);
    endpoints.MapActorsHandlers();
    endpoints.MapSubscribeHandler();
});

app.UseCloudEvents();

app.MapPost("/developers", [Topic(Consts.PubSub, Consts.MainTopic, 
    $"(event.type ==\"{nameof(GithubFlowEventType.CodeGenerationRequested)}\") || (event.type ==\"{nameof(GithubFlowEventType.CodeGenerationRequested)}\")", 1)] 
    async (IActorProxyFactory proxyFactory, EventEnvelope evt) =>  await HandleEvent(proxyFactory,nameof(Dev), nameof(Dev.HandleEvent), evt));

app.MapPost("/devleads", [Topic(Consts.PubSub, Consts.MainTopic,
$"(event.type ==\"{nameof(GithubFlowEventType.DevPlanRequested)}\") || (event.type ==\"{nameof(GithubFlowEventType.DevPlanChainClosed)}\")", 2)] 
async (IActorProxyFactory proxyFactory, EventEnvelope evt) => await HandleEvent(proxyFactory, nameof(DeveloperLead), nameof(DeveloperLead.HandleEvent), evt));

app.MapPost("/productmanagers", [Topic(Consts.PubSub, Consts.MainTopic, 
$"(event.type ==\"{nameof(GithubFlowEventType.ReadmeRequested)}\") || (event.type ==\"{nameof(GithubFlowEventType.ReadmeChainClosed)}\")", 3)]
async (IActorProxyFactory proxyFactory, EventEnvelope evt) =>  await HandleEvent(proxyFactory, nameof(ProductManager), nameof(ProductManager.HandleEvent), evt));

app.MapPost("/hubbers", [Topic(Consts.PubSub, Consts.MainTopic,
 $"(event.type ==\"{nameof(GithubFlowEventType.NewAsk)}\") || (event.type ==\"{nameof(GithubFlowEventType.ReadmeGenerated)}\") || (event.type ==\"{nameof(GithubFlowEventType.DevPlanGenerated)}\") || (event.type ==\"{nameof(GithubFlowEventType.CodeGenerated)}\") || (event.type ==\"{nameof(GithubFlowEventType.DevPlanCreated)}\") || (event.type ==\"{nameof(GithubFlowEventType.ReadmeStored)}\") || (event.type ==\"{nameof(GithubFlowEventType.SandboxRunFinished)}\")", 4)]
 async (IActorProxyFactory proxyFactory, EventEnvelope evt) =>  await HandleEvent(proxyFactory, nameof(Hubber), nameof(Hubber.HandleEvent), evt));

app.MapPost("/azuregenies", [Topic(Consts.PubSub, Consts.MainTopic,  
$"(event.type ==\"{nameof(GithubFlowEventType.ReadmeCreated)}\") || (event.type ==\"{nameof(GithubFlowEventType.CodeCreated)}\")", 5)]
async (IActorProxyFactory proxyFactory, EventEnvelope evt) => await HandleEvent(proxyFactory, nameof(AzureGenie), nameof(AzureGenie.HandleEvent), evt));

app.MapPost("/sandboxes", [Topic(Consts.PubSub, Consts.MainTopic,$"(event.type ==\"{nameof(GithubFlowEventType.SandboxRunCreated)}\")", 6)] 
async (IActorProxyFactory proxyFactory, EventEnvelope evt) => await HandleEvent(proxyFactory, nameof(Sandbox), nameof(Sandbox.HandleEvent), evt));

app.Run();

static async Task HandleEvent(IActorProxyFactory proxyFactory, string type, string method, EventEnvelope evt)
{
    try
    {
        var proxyOptions = new ActorProxyOptions
        {
            RequestTimeout = Timeout.InfiniteTimeSpan
        };
        var proxy = proxyFactory.Create(new ActorId(evt.Data.Subject), type, proxyOptions);
        await proxy.InvokeMethodAsync(method, evt.Data);
    }
    catch (Exception ex)
    {
        throw;
    }
}

static ISemanticTextMemory CreateMemory(IServiceProvider provider)
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

    var memoryBuilder = new MemoryBuilder();
    return memoryBuilder.WithLoggerFactory(loggerFactory)
                 .WithQdrantMemoryStore(qdrantConfig.Endpoint, qdrantConfig.VectorSize)
                 .WithAzureOpenAITextEmbeddingGeneration(openAiConfig.EmbeddingDeploymentOrModelId, openAiConfig.Endpoint, openAiConfig.ApiKey)
                 .Build();
}

static Kernel CreateKernel(IServiceProvider provider)
{
    var openAiConfig = provider.GetService<IOptions<OpenAIOptions>>().Value;
    var clientOptions = new OpenAIClientOptions();
    clientOptions.Retry.NetworkTimeout = TimeSpan.FromMinutes(5);
    var openAIClient = new OpenAIClient(new Uri(openAiConfig.Endpoint), new AzureKeyCredential(openAiConfig.ApiKey), clientOptions);
    var builder = Kernel.CreateBuilder();
    builder.Services.AddLogging(c => c.AddConsole().AddDebug().SetMinimumLevel(LogLevel.Debug));
    builder.Services.AddAzureOpenAIChatCompletion(openAiConfig.DeploymentOrModelId, openAIClient);
    builder.Services.ConfigureHttpClientDefaults(c =>
    {
        c.AddStandardResilienceHandler().Configure(o =>
        {
            o.Retry.MaxRetryAttempts = 5;
            o.Retry.BackoffType = Polly.DelayBackoffType.Exponential;
        });
    });
    return builder.Build();
}