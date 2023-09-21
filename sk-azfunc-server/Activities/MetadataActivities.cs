using System.Runtime.CompilerServices;
using System.Text.Json;
using Azure.Data.Tables;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Azure.Functions.Worker.Http;
using Microsoft.Extensions.Logging;

namespace SK.DevTeam
{
    [System.Diagnostics.CodeAnalysis.SuppressMessage("Usage", "CA2007: Do not directly await a Task", Justification = "Durable functions")]
    public static class MetadataActivities
    {
        [Function(nameof(GetMetadata))]
        public static async Task<IssueMetadata> GetMetadata(
            [HttpTrigger(AuthorizationLevel.Anonymous, "get", Route = "metadata/{key}")] HttpRequestData req, string key,
            [TableInput("Metadata", Connection = "AzureWebJobsStorage")] TableClient client,
            FunctionContext executionContext)
        {
            var logger = executionContext.GetLogger<SKWebHookEventProcessor>();

            logger.LogInformation($"Getting metadata for {key}");

            var metadataResponse = await client.GetEntityAsync<IssueMetadata>(key, key);
            var metadata = metadataResponse.Value;

            logger.LogInformation($"Metadata result {JsonSerializer.Serialize(metadata)}");

            return metadata;
        }

        [Function(nameof(SaveMetadata))]

        public static async Task<IssueMetadata> SaveMetadata(
            [ActivityTrigger] IssueMetadata metadata,
            [TableInput("Metadata", Connection = "AzureWebJobsStorage")] TableClient client,
            FunctionContext executionContext)
        {
            await client.UpsertEntityAsync(metadata);
            return metadata;
        }
    }
}
