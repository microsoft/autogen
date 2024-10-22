using Microsoft.Extensions.AI;
using Azure.AI.Inference;

namespace Microsoft.AutoGen.Extensions.AzureAIInference
{
    public static class AzureOpenAIClient : IChatClient
    {
        public static IChatClient UseAzureOpenAI(this IChatClientBuilder builder)
        {
            builder.UseLogging()
                .UseFunctionInvocation()
                .UseOpenTelemetry()
                .UseAzureOpenAI();
            return builder.Build();
        }

        public IChatClient AzureAIInference(
        {
            IChatClient client = new ChatCompletionsClient(
                endpoint: new Uri("https://models.inference.ai.azure.com"), 
                new AzureKeyCredential(Environment.GetEnvironmentVariable("GH_TOKEN")))
                .AsChatClient("Phi-3.5-MoE-instruct");
        }


    }
}