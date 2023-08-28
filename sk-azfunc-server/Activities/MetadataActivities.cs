using Azure.Data.Tables;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Azure.Functions.Worker;

namespace SK.DevTeam
{
    [System.Diagnostics.CodeAnalysis.SuppressMessage("Usage", "CA2007: Do not directly await a Task", Justification = "Durable functions")]
    public static class MetadataActivities
    {
        [Function(nameof(GetMetadata))]
        public static async Task<IActionResult> GetMetadata(
            [HttpTrigger(AuthorizationLevel.Anonymous, "get", Route = "metadata/{key}")] HttpRequest req,
            [TableInput("Metadata", Connection = "AzureWebJobsStorage")] TableClient client,
            FunctionContext executionContext)
        {
            var key = req.RouteValues["key"].ToString();
            var metadataResponse = await client.GetEntityAsync<IssueMetadata>(key, key);
            var metadata = metadataResponse.Value;
            return new OkObjectResult(metadata);
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
