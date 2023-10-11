using System.Text.Json;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.AI.OpenAI.TextEmbedding;
using Microsoft.SemanticKernel.Connectors.Memory.Qdrant;
using Microsoft.SemanticKernel.Memory;
using Octokit.Webhooks;
using Octokit.Webhooks.AzureFunctions;

namespace KernelHttpServer;

public static class Program
{
    public static void Main()
    {
        var host = new HostBuilder()
            .ConfigureFunctionsWorkerDefaults()
            .ConfigureGitHubWebhooks()
            .ConfigureAppConfiguration(configuration =>
            {
                var config = configuration.SetBasePath(Directory.GetCurrentDirectory())
                    .AddJsonFile("local.settings.json", optional: true, reloadOnChange: true)
                    .AddEnvironmentVariables();

                var builtConfig = config.Build();
            })
            .ConfigureServices(services =>
            {
                services.AddTransient((provider) => CreateKernel(provider));
                services.AddScoped<GithubService>();
                services.AddScoped<WebhookEventProcessor, SKWebHookEventProcessor>();
                services.AddOptions<GithubOptions>()
                    .Configure<IConfiguration>((settings, configuration) =>
                    {
                        configuration.GetSection("GithubOptions").Bind(settings);
                    });
                services.AddOptions<AzureOptions>()
                    .Configure<IConfiguration>((settings, configuration) =>
                    {
                        configuration.GetSection("AzureOptions").Bind(settings);
                    });
                services.AddOptions<OpenAIOptions>()
                    .Configure<IConfiguration>((settings, configuration) =>
                    {
                        configuration.GetSection("OpenAIOptions").Bind(settings);
                    });
                services.AddOptions<QdrantOptions>()
                    .Configure<IConfiguration>((settings, configuration) =>
                    {
                        configuration.GetSection("QdrantOptions").Bind(settings);
                    });
                services.AddApplicationInsightsTelemetryWorkerService();
                services.ConfigureFunctionsApplicationInsights();
                // return JSON with expected lowercase naming
                services.Configure<JsonSerializerOptions>(options =>
                {
                    options.PropertyNamingPolicy = JsonNamingPolicy.CamelCase;
                });


                services.AddHttpClient("FunctionsClient", client =>
                {
                    var fqdn = Environment.GetEnvironmentVariable("FUNCTIONS_FQDN", EnvironmentVariableTarget.Process);
                    client.BaseAddress = new Uri($"{fqdn}/api/");
                });
            })
            .ConfigureLogging(logging =>
            {
                logging.Services.Configure<LoggerFilterOptions>(options =>
                {
                    LoggerFilterRule defaultRule = options.Rules.FirstOrDefault(rule => rule.ProviderName
                        == "Microsoft.Extensions.Logging.ApplicationInsights.ApplicationInsightsLoggerProvider");
                    if (defaultRule is not null)
                    {
                        options.Rules.Remove(defaultRule);
                    }
                });
            })
            .Build();

        host.Run();
    }

    private static IKernel CreateKernel(IServiceProvider provider)
    {
        var openAiConfig = provider.GetService<IOptions<OpenAIOptions>>().Value;
        var qdrantConfig = provider.GetService<IOptions<QdrantOptions>>().Value;


        using ILoggerFactory loggerFactory = LoggerFactory.Create(builder =>
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
                            .WithMemory(semanticTextMemory)
                            .Build();
    }
}
