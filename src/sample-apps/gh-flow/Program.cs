using System.Text.Json;
using Azure;
using Azure.AI.OpenAI;
using Microsoft.AI.DevTeam;
using Microsoft.Extensions.Options;
using Microsoft.SemanticKernel;
using Octokit.Webhooks;
using Octokit.Webhooks.AspNetCore;
using Azure.Identity;
using Microsoft.Extensions.Azure;
using Microsoft.Extensions.Http.Resilience;
using Microsoft.KernelMemory;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddSingleton<WebhookEventProcessor, GithubWebHookProcessor>();
builder.Services.AddTransient(CreateKernel);
builder.Services.AddSingleton<IKernelMemory>(CreateMemory);
builder.Services.AddHttpClient();

builder.Services.AddSingleton(s =>
{
    var ghOptions = s.GetService<IOptions<GithubOptions>>();
    var logger = s.GetService<ILogger<GithubAuthService>>();
    var ghService = new GithubAuthService(ghOptions, logger);
    var client = ghService.GetGitHubClient().Result;
    return client;
});


builder.Services.AddAzureClients(clientBuilder =>
{
    clientBuilder.UseCredential(new DefaultAzureCredential());
    clientBuilder.AddArmClient(default);
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

    siloBuilder.UseLocalhostClustering()
               .AddMemoryStreams("StreamProvider")
               .AddMemoryGrainStorage("PubSubStore")
               .AddMemoryGrainStorage("messages");
    siloBuilder.UseInMemoryReminderService();
    siloBuilder.UseDashboard(x => x.HostSelf = true);

});

builder.Services.Configure<JsonSerializerOptions>(options =>
{
    options.PropertyNamingPolicy = JsonNamingPolicy.CamelCase;
});
var app = builder.Build();

app.UseRouting()
   .UseEndpoints(endpoints =>
{
    var ghOptions = app.Services.GetService<IOptions<GithubOptions>>().Value;
    endpoints.MapGitHubWebhooks(secret: ghOptions.WebhookSecret );
});

app.Map("/dashboard", x => x.UseOrleansDashboard());

app.Run();

static IKernelMemory CreateMemory(IServiceProvider provider)
{
    var qdrantConfig = provider.GetService<IOptions<QdrantOptions>>().Value;
    var openAiConfig = provider.GetService<IOptions<OpenAIOptions>>().Value;
    return new KernelMemoryBuilder()
            .WithQdrantMemoryDb(qdrantConfig.Endpoint)
            .WithAzureOpenAITextGeneration(new AzureOpenAIConfig
            {
                APIType = AzureOpenAIConfig.APITypes.ChatCompletion,
                Endpoint = openAiConfig.Endpoint,
                Deployment = openAiConfig.DeploymentOrModelId,
                Auth = AzureOpenAIConfig.AuthTypes.APIKey,
                APIKey = openAiConfig.ApiKey
            })
            .WithAzureOpenAITextEmbeddingGeneration(new AzureOpenAIConfig
            {
                APIType = AzureOpenAIConfig.APITypes.EmbeddingGeneration,
                Endpoint = openAiConfig.Endpoint,
                Deployment =openAiConfig.EmbeddingDeploymentOrModelId,
                Auth = AzureOpenAIConfig.AuthTypes.APIKey,
               APIKey = openAiConfig.ApiKey
            })
            .Build<MemoryServerless>();
}

static Kernel CreateKernel(IServiceProvider provider)
{
    var openAiConfig = provider.GetService<IOptions<OpenAIOptions>>().Value;
    var clientOptions = new OpenAIClientOptions();
    clientOptions.Retry.NetworkTimeout = TimeSpan.FromMinutes(5);
    var openAIClient = new OpenAIClient(new Uri(openAiConfig.Endpoint), new AzureKeyCredential(openAiConfig.ApiKey), clientOptions);
    var builder = Kernel.CreateBuilder();
    builder.Services.AddLogging( c=> c.AddConsole().AddDebug().SetMinimumLevel(LogLevel.Debug));
    builder.Services.AddAzureOpenAIChatCompletion(openAiConfig.DeploymentOrModelId, openAIClient);
    builder.Services.ConfigureHttpClientDefaults(c=>
    {
        c.AddStandardResilienceHandler().Configure( o=> {
            o.Retry.MaxRetryAttempts = 5;
            o.Retry.BackoffType = Polly.DelayBackoffType.Exponential;
        });
    });
    return builder.Build();
}