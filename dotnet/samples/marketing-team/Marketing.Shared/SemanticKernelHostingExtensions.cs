// Copyright (c) Microsoft Corporation. All rights reserved.
// SemanticKernelHostingExtensions.cs

using System.ClientModel;
using System.Text.Json;
using Azure.AI.OpenAI;
using Marketing.Shared.Options;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Connectors.OpenAI;
using Microsoft.SemanticKernel.Memory;
using OpenAI;

namespace Marketing.Shared;
public static class SemanticKernelHostingExtensions
{
    public static IHostApplicationBuilder ConfigureSemanticKernel(this IHostApplicationBuilder builder)
    {
        builder.Services.AddTransient(CreateKernel);
        builder.Services.AddTransient(CreateMemory);

        builder.Services.Configure<OpenAIOptions>(o =>
        {
            o.EmbeddingsEndpoint = o.ImageEndpoint = o.ChatEndpoint = builder.Configuration["OpenAI:Endpoint"] ?? throw new InvalidOperationException("Ensure that OpenAI:Endpoint is set in configuration");
            o.EmbeddingsApiKey = o.ImageApiKey = o.ChatApiKey = builder.Configuration["OpenAI:Key"]!;
            o.EmbeddingsDeploymentOrModelId = "text-embedding-ada-002";
            o.ImageDeploymentOrModelId = "dall-e-3";
            o.ChatDeploymentOrModelId = "gpt-4o";
        });

        builder.Services.Configure<AzureOpenAIClientOptions>(o =>
        {
            o.NetworkTimeout = TimeSpan.FromMinutes(3);
        });

        builder.Services.Configure<JsonSerializerOptions>(options =>
        {
            options.PropertyNamingPolicy = JsonNamingPolicy.CamelCase;
        });
        return builder;
    }

    public static ISemanticTextMemory CreateMemory(IServiceProvider provider)
    {
        var openAiConfig = provider.GetRequiredService<IOptions<OpenAIOptions>>().Value;
        var loggerFactory = provider.GetRequiredService<ILoggerFactory>();
        var memoryBuilder = new MemoryBuilder();
#pragma warning disable SKEXP0050 // Type is for evaluation purposes only and is subject to change or removal in future updates. Suppress this diagnostic to proceed.
        return memoryBuilder.WithLoggerFactory(loggerFactory)
                     .WithMemoryStore(new VolatileMemoryStore())
                     .WithOpenAITextEmbeddingGeneration(openAiConfig.EmbeddingsDeploymentOrModelId, openAiConfig.EmbeddingsEndpoint, openAiConfig.EmbeddingsApiKey)
                     .Build();
#pragma warning restore SKEXP0050 // Type is for evaluation purposes only and is subject to change or removal in future updates. Suppress this diagnostic to proceed.
    }

    public static Kernel CreateKernel(IServiceProvider provider)
    {
        OpenAIOptions openAiConfig = provider.GetRequiredService<IOptions<OpenAIOptions>>().Value;
        var builder = Kernel.CreateBuilder();

        // Chat
        if (openAiConfig.ChatEndpoint.Contains(".azure", StringComparison.OrdinalIgnoreCase))
        {
            var openAIClient = new AzureOpenAIClient(new Uri(openAiConfig.ChatEndpoint), new ApiKeyCredential(openAiConfig.ChatApiKey));
            builder.Services.AddAzureOpenAIChatCompletion(openAiConfig.ChatDeploymentOrModelId, openAIClient);
        }
        else
        {
            var openAIClient = new OpenAIClient(openAiConfig.ChatApiKey);
            builder.Services.AddOpenAIChatCompletion(openAiConfig.ChatDeploymentOrModelId, openAIClient);
        }

        // Text to Image
        if (openAiConfig.ImageEndpoint.Contains(".azure", StringComparison.OrdinalIgnoreCase))
        {
            ArgumentException.ThrowIfNullOrEmpty(openAiConfig.ImageDeploymentOrModelId);
            var openAIClient = new AzureOpenAIClient(new Uri(openAiConfig.ImageEndpoint), new ApiKeyCredential(openAiConfig.ImageApiKey));
            builder.Services.AddAzureOpenAITextToImage(openAiConfig.ImageDeploymentOrModelId, openAIClient);
        }
        else
        {
            builder.Services.AddOpenAITextToImage(openAiConfig.ImageApiKey, modelId: openAiConfig.ImageDeploymentOrModelId);
        }

        // Embeddings
        if (openAiConfig.EmbeddingsEndpoint.Contains(".azure", StringComparison.OrdinalIgnoreCase))
        {
            var openAIClient = new AzureOpenAIClient(new Uri(openAiConfig.EmbeddingsEndpoint), new ApiKeyCredential(openAiConfig.EmbeddingsApiKey));
            builder.Services.AddAzureOpenAITextEmbeddingGeneration(openAiConfig.EmbeddingsDeploymentOrModelId, openAIClient);
        }
        else
        {
            var openAIClient = new OpenAIClient(openAiConfig.EmbeddingsApiKey);
            builder.Services.AddOpenAITextEmbeddingGeneration(openAiConfig.EmbeddingsDeploymentOrModelId, openAIClient);
        }

        return builder.Build();
    }
}
