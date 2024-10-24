// Copyright (c) Microsoft. All rights reserved.

using System.Text.Json;
using Azure.AI.OpenAI;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.OpenAI;
using Microsoft.SemanticKernel.Connectors.Qdrant;
using Microsoft.SemanticKernel.Memory;

namespace Microsoft.AutoGen.Extensions.SemanticKernel;
public static class SemanticKernelHostingExtensions
{
    public static IHostApplicationBuilder ConfigureSemanticKernel(this IHostApplicationBuilder builder)
    {
        builder.Services.Configure<AIClientOptions>(o =>
        {
            o.EmbeddingsEndpoint = o.ImageEndpoint = o.ChatEndpoint = builder.Configuration["OpenAI:Endpoint"] ?? throw new InvalidOperationException("Ensure that OpenAI:Endpoint is set in configuration");
            o.EmbeddingsApiKey = o.ImageApiKey = o.ChatApiKey = builder.Configuration["OpenAI:Key"]!;
            o.EmbeddingsDeploymentOrModelId = "text-embedding-3-large";
            o.ImageDeploymentOrModelId = "dall-e-3";
            o.ChatDeploymentOrModelId = "gpt-4o";
        });

        builder.Services.Configure<AzureOpenAIClientOptions>(o =>
        {
            o.NetworkTimeout = TimeSpan.FromMinutes(5);
        });

        builder.Services.AddOptions<QdrantOptions>().Bind(builder.Configuration.GetSection("Qdrant"))
            .ValidateDataAnnotations()
            .ValidateOnStart();

        builder.Services.Configure<JsonSerializerOptions>(options =>
        {
            options.PropertyNamingPolicy = JsonNamingPolicy.CamelCase;
        });

        builder.Services.AddTransient(CreateKernel);
        builder.Services.AddTransient(CreateMemory);
        return builder;
    }

    private static ISemanticTextMemory CreateMemory(IServiceProvider provider)
    {
        var qdrantConfig = provider.GetRequiredService<IOptions<QdrantOptions>>().Value;
        var openAiConfig = provider.GetRequiredService<IOptions<AIClientOptions>>().Value;
        var qdrantHttpClient = new HttpClient();
        if (!string.IsNullOrEmpty(qdrantConfig.ApiKey))
        {
            qdrantHttpClient.DefaultRequestHeaders.Add("api-key", qdrantConfig.ApiKey);
        }
        var loggerFactory = provider.GetRequiredService<ILoggerFactory>();
        var memoryBuilder = new MemoryBuilder();
        return memoryBuilder.WithLoggerFactory(loggerFactory)
                    .WithQdrantMemoryStore(qdrantHttpClient, qdrantConfig.VectorSize, qdrantConfig.Endpoint)
                    .WithOpenAITextEmbeddingGeneration(openAiConfig.EmbeddingsDeploymentOrModelId, openAiConfig.EmbeddingsApiKey)
                    .Build();
    }

    private static Kernel CreateKernel(IServiceProvider provider)
    {
        AIClientOptions openAiConfig = provider.GetRequiredService<IOptions<AIClientOptions>>().Value;
        var builder = Kernel.CreateBuilder();

        // Chat
        if (openAiConfig.ChatEndpoint.Contains(".azure", StringComparison.OrdinalIgnoreCase))
        {
            //var openAIClient = new OpenAIClient(new Uri(openAiConfig.ChatEndpoint), new Azure.AzureKeyCredential(openAiConfig.ChatApiKey));
            builder.Services.AddAzureOpenAIChatCompletion(deploymentName: openAiConfig.ChatDeploymentOrModelId, apiKey: openAiConfig.ChatApiKey, endpoint: openAiConfig.ChatEndpoint);
        }
        else
        {
            builder.Services.AddOpenAIChatCompletion(apiKey: openAiConfig.ChatApiKey, modelId: openAiConfig.ChatDeploymentOrModelId);
        }

        // Text to Image
        if (openAiConfig.ImageEndpoint.Contains(".azure", StringComparison.OrdinalIgnoreCase))
        {
            ArgumentException.ThrowIfNullOrEmpty(openAiConfig.ImageDeploymentOrModelId);
            builder.Services.AddAzureOpenAITextToImage(openAiConfig.ImageApiKey, openAiConfig.ImageDeploymentOrModelId, openAiConfig.ImageEndpoint);
        }
        else
        {
            builder.Services.AddOpenAITextToImage(openAiConfig.ImageApiKey, modelId: openAiConfig.ImageDeploymentOrModelId);
        }

        // Embeddings
        if (openAiConfig.EmbeddingsEndpoint.Contains(".azure", StringComparison.OrdinalIgnoreCase))
        {
            builder.Services.AddAzureOpenAITextEmbeddingGeneration(openAiConfig.EmbeddingsDeploymentOrModelId, openAiConfig.EmbeddingsApiKey, openAiConfig.EmbeddingsEndpoint);
        }
        else
        {
            builder.Services.AddOpenAITextEmbeddingGeneration(modelId: openAiConfig.EmbeddingsDeploymentOrModelId);
        }

        return builder.Build();
    }
}
