// Copyright (c) Microsoft Corporation. All rights reserved.
// ServiceCollectionChatCompletionExtensions.cs

using System.ClientModel;
using System.Data.Common;
using Azure;
using Azure.AI.Inference;
using Azure.AI.OpenAI;
using Microsoft.Extensions.AI;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using OpenAI;

namespace Microsoft.Extensions.Hosting;
public static class ServiceCollectionChatClientExtensions
{
    public static IServiceCollection AddOllamaChatClient(
        this IHostApplicationBuilder hostBuilder,
        string serviceName,
        Func<ChatClientBuilder, ChatClientBuilder>? builder = null,
        string? modelName = null)
    {
        if (modelName is null)
        {
            var configKey = $"{serviceName}:LlmModelName";
            modelName = hostBuilder.Configuration[configKey];
            if (string.IsNullOrEmpty(modelName))
            {
                throw new InvalidOperationException($"No {nameof(modelName)} was specified, and none could be found from configuration at '{configKey}'");
            }
        }
        return hostBuilder.Services.AddOllamaChatClient(
            modelName,
            new Uri($"http://{serviceName}"),
            builder);
    }
    public static IServiceCollection AddOllamaChatClient(
        this IServiceCollection services,
        string modelName,
        Uri? uri = null,
        Func<ChatClientBuilder, ChatClientBuilder>? builder = null)
    {
        uri ??= new Uri("http://localhost:11434");
        return services.AddChatClient(pipeline =>
        {
            builder?.Invoke(pipeline);
            var httpClient = pipeline.Services.GetService<HttpClient>() ?? new();
            return pipeline.Use(new OllamaChatClient(uri, modelName, httpClient));
        });
    }
    public static IServiceCollection AddOpenAIChatClient(
        this IHostApplicationBuilder hostBuilder,
        string serviceName,
        Func<ChatClientBuilder, ChatClientBuilder>? builder = null,
        string? modelOrDeploymentName = null)
    {
        // TODO: We would prefer to use Aspire.AI.OpenAI here, 
        var connectionString = hostBuilder.Configuration.GetConnectionString(serviceName);
        if (string.IsNullOrWhiteSpace(connectionString))
        {
            throw new InvalidOperationException($"No connection string named '{serviceName}' was found. Ensure a corresponding Aspire service was registered.");
        }
        var connectionStringBuilder = new DbConnectionStringBuilder();
        connectionStringBuilder.ConnectionString = connectionString;
        var endpoint = (string?)connectionStringBuilder["endpoint"];
        var apiKey = (string)connectionStringBuilder["key"] ?? throw new InvalidOperationException($"The connection string named '{serviceName}' does not specify a value for 'Key', but this is required.");

        modelOrDeploymentName ??= (connectionStringBuilder["Deployment"] ?? connectionStringBuilder["Model"]) as string;
        if (string.IsNullOrWhiteSpace(modelOrDeploymentName))
        {
            throw new InvalidOperationException($"The connection string named '{serviceName}' does not specify a value for 'Deployment' or 'Model', and no value was passed for {nameof(modelOrDeploymentName)}.");
        }

        var endpointUri = string.IsNullOrEmpty(endpoint) ? null : new Uri(endpoint);
        return hostBuilder.Services.AddOpenAIChatClient(apiKey, modelOrDeploymentName, endpointUri, builder);
    }
    public static IServiceCollection AddOpenAIChatClient(
        this IServiceCollection services,
        string apiKey,
        string modelOrDeploymentName,
        Uri? endpoint = null,
        Func<ChatClientBuilder, ChatClientBuilder>? builder = null)
    {
        return services
            .AddSingleton(_ => endpoint is null
                ? new OpenAIClient(apiKey)
                : new AzureOpenAIClient(endpoint, new ApiKeyCredential(apiKey)))
            .AddChatClient(pipeline =>
            {
                builder?.Invoke(pipeline);
                var openAiClient = pipeline.Services.GetRequiredService<OpenAIClient>();
                return pipeline.Use(openAiClient.AsChatClient(modelOrDeploymentName));
            });
    }
    public static IServiceCollection AddAzureChatClient(
        this IHostApplicationBuilder hostBuilder,
        string serviceName,
        Func<ChatClientBuilder, ChatClientBuilder>? builder = null,
        string? modelOrDeploymentName = null)
    {
        if (modelOrDeploymentName is null)
        {
            var configKey = $"{serviceName}:LlmModelName";
            modelOrDeploymentName = hostBuilder.Configuration[configKey];
            if (string.IsNullOrEmpty(modelOrDeploymentName))
            {
                throw new InvalidOperationException($"No {nameof(modelOrDeploymentName)} was specified, and none could be found from configuration at '{configKey}'");
            }
        }
        var endpoint = $"{serviceName}:Endpoint" ?? throw new InvalidOperationException($"No endpoint was specified for the Azure Inference Chat Client");
        var endpointUri = string.IsNullOrEmpty(endpoint) ? null : new Uri(endpoint);
        return hostBuilder.Services.AddChatClient(pipeline =>
        {
            builder?.Invoke(pipeline);
            var token = Environment.GetEnvironmentVariable("GH_TOKEN") ?? throw new InvalidOperationException("No model access token was found in the environment variable GH_TOKEN");
            return pipeline.Use(new ChatCompletionsClient(
            endpointUri, new AzureKeyCredential(token)).AsChatClient(modelOrDeploymentName));
        });
    }
}
