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

            if (builder.Configuration[$"{serviceName}:Type"] == "ollama")
            {
                builder.AddOllamaChatClient(serviceName, pipeline);
            }
            else if (builder.Configuration[$"{serviceName}:Type"] == "openai")
            {
                builder.AddOpenAIChatClient(serviceName, pipeline);
            }
            else if (builder.Configuration[$"{serviceName}:Type"] == "azureaiinference")
            {
                builder.AddAzureChatClient(serviceName, pipeline);
            }
            else
            {
                throw new InvalidOperationException("Did not find a valid model implementation for the given service name ${serviceName}");
            }
            return builder;
        }
    }
}