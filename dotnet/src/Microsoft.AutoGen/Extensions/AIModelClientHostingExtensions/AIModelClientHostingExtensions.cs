using Microsoft.Extensions.AI;

namespace Microsoft.Extensions.Hosting
{
    public static class AIModelClient
    {
        public static IHostApplicationBuilder AddChatCompletionService(this IHostApplicationBuilder builder, string serviceName)
        {
            var pipeline = (ChatClientBuilder pipeline) => pipeline
            .UseLogging()
            .UseFunctionInvocation()
            .UseOpenTelemetry(configure: c => c.EnableSensitiveData = true);

            if (builder.Configuration[$"{serviceName}:ModelType"] == "ollama")
            {
                builder.AddOllamaChatClient(serviceName, pipeline);
            }
            else if (builder.Configuration[$"{serviceName}:ModelType"] == "openai" || builder.Configuration[$"{serviceName}:ModelType"] == "azureopenai")
            {
                builder.AddOpenAIChatClient(serviceName, pipeline);
            }
            else if (builder.Configuration[$"{serviceName}:ModelType"] == "azureaiinference")
            {
                builder.AddAzureChatClient(serviceName, pipeline);
            }
            else
            {
                throw new InvalidOperationException("Did not find a valid model implementation for the given service name ${serviceName}, valid supported implemenation types are ollama, openai, azureopenai, azureaiinference");
            }
            return builder;
        }
    }
}
