using UglyToad.PdfPig;
using UglyToad.PdfPig.DocumentLayoutAnalysis.TextExtractor;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Text;
using Microsoft.Extensions.Logging;
using System.Text;
using Microsoft.SemanticKernel.Connectors.Memory.Qdrant;
using Microsoft.SemanticKernel.Connectors.AI.OpenAI.TextEmbedding;
using Microsoft.SemanticKernel.Memory;
using System.Reflection;

class Program
{
    static string WafFileName = "azure-well-architected.pdf";
    static async Task Main(string[] args)
    {
        var kernelSettings = KernelSettings.LoadSettings();
        var kernelConfig = new KernelConfig();

        using ILoggerFactory loggerFactory = LoggerFactory.Create(builder =>
        {
            builder
                .SetMinimumLevel(kernelSettings.LogLevel ?? LogLevel.Warning)
                .AddConsole()
                .AddDebug();
        });
       
        var memoryStore = new QdrantMemoryStore(new QdrantVectorDbClient("http://qdrant", 1536, port: 6333));
        var embedingGeneration = new AzureTextEmbeddingGeneration(kernelSettings.EmbeddingDeploymentOrModelId, kernelSettings.Endpoint, kernelSettings.ApiKey);
        var semanticTextMemory = new SemanticTextMemory(memoryStore, embedingGeneration);

        var kernel = new KernelBuilder()
                            .WithLogger(loggerFactory.CreateLogger<IKernel>())
                            .WithAzureChatCompletionService(kernelSettings.DeploymentOrModelId, kernelSettings.Endpoint, kernelSettings.ApiKey, true, kernelSettings.ServiceId, true)
                            .WithMemory(semanticTextMemory)
                            .WithConfiguration(kernelConfig).Build();
        await ImportDocumentAsync(kernel, WafFileName);
    }

    public static async Task ImportDocumentAsync(IKernel kernel, string filename)
        {
            var currentDirectory = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            var filePath = Path.Combine(currentDirectory, filename);
            using var pdfDocument = PdfDocument.Open(File.OpenRead(filePath));
            var pages = pdfDocument.GetPages();
            foreach (var page in pages)
            {
                var text = ContentOrderTextExtractor.GetText(page);
                var descr = text.Take(100);
                await kernel.Memory.SaveInformationAsync(
                    collection: "waf-pages",
                    text: text,
                    id: $"{Guid.NewGuid()}",
                    description: $"Document: {descr}");
            }
        }
}