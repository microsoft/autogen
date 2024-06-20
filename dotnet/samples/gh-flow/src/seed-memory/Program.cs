using System.Reflection;
using Microsoft.Extensions.Logging;
using Microsoft.SemanticKernel.Connectors.OpenAI;
using Microsoft.SemanticKernel.Connectors.Qdrant;
using Microsoft.SemanticKernel.Memory;
using UglyToad.PdfPig;
using UglyToad.PdfPig.DocumentLayoutAnalysis.TextExtractor;

public sealed class Program
{
    private const string WafFileName = "azure-well-architected.pdf";
    static async Task Main()
    {
        var kernelSettings = KernelSettings.LoadSettings();

        using ILoggerFactory loggerFactory = LoggerFactory.Create(builder =>
        {
            builder
                .SetMinimumLevel(kernelSettings.LogLevel ?? LogLevel.Warning)
                .AddConsole()
                .AddDebug();
        });

        var memoryBuilder = new MemoryBuilder();
        var memory = memoryBuilder.WithLoggerFactory(loggerFactory)
                    .WithQdrantMemoryStore(kernelSettings.QdrantEndpoint, 1536)
                    .WithAzureOpenAITextEmbeddingGeneration(kernelSettings.EmbeddingDeploymentOrModelId, kernelSettings.Endpoint, kernelSettings.ApiKey)
                    .Build();

        await ImportDocumentAsync(memory, WafFileName).ConfigureAwait(false);
    }

    public static async Task ImportDocumentAsync(ISemanticTextMemory memory, string filename)
    {
        var asm = Assembly.GetExecutingAssembly();
        var currentDirectory = Path.GetDirectoryName(asm.Location);
        if (currentDirectory is null)
        {
            throw new DirectoryNotFoundException($"Could not find directory for assembly '{asm}'.");
        }

        var filePath = Path.Combine(currentDirectory, filename);
        using var pdfDocument = PdfDocument.Open(File.OpenRead(filePath));
        var pages = pdfDocument.GetPages();
        foreach (var page in pages)
        {
            try
            {
                var text = ContentOrderTextExtractor.GetText(page);
                var descr = text.Take(100);
                await memory.SaveInformationAsync(
                    collection: "waf",
                    text: text,
                    id: $"{Guid.NewGuid()}",
                    description: $"Document: {descr}").ConfigureAwait(false);
            }
            catch (Exception ex)
            {
                Console.WriteLine(ex.Message);
            }
        }
    }
}