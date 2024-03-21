using Microsoft.Extensions.Logging;
using Microsoft.KernelMemory;

class Program
{
    static string WafFileName = "azure-well-architected.pdf";
    static async Task Main(string[] args)
    {
        var kernelSettings = KernelSettings.LoadSettings();

        using ILoggerFactory loggerFactory = LoggerFactory.Create(builder =>
        {
            builder
                .SetMinimumLevel(kernelSettings.LogLevel ?? LogLevel.Warning)
                .AddConsole()
                .AddDebug();
        });

        var memory = new KernelMemoryBuilder()
                .WithQdrantMemoryDb(kernelSettings.QdrantEndpoint)
                .WithAzureOpenAITextGeneration(new AzureOpenAIConfig
                {
                    APIType = AzureOpenAIConfig.APITypes.ChatCompletion,
                    Endpoint =kernelSettings.Endpoint,
                    Deployment = kernelSettings.DeploymentOrModelId,
                    Auth = AzureOpenAIConfig.AuthTypes.APIKey,
                    APIKey = kernelSettings.ApiKey
                })
                .WithAzureOpenAITextEmbeddingGeneration(new AzureOpenAIConfig
                {
                    APIType = AzureOpenAIConfig.APITypes.EmbeddingGeneration,
                    Endpoint = kernelSettings.Endpoint,
                    Deployment =kernelSettings.EmbeddingDeploymentOrModelId,
                    Auth = AzureOpenAIConfig.AuthTypes.APIKey,
                APIKey = kernelSettings.ApiKey
                })
                .Build<MemoryServerless>();
        await ImportDocumentAsync(memory, WafFileName);
    }

    public static async Task ImportDocumentAsync(IKernelMemory memory, string filename)
        {
            await memory.ImportDocumentAsync(new Document("wafdoc")
                                            .AddFiles([
                                                filename
                                            ]), index: "waf");
        }
}