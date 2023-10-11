using Azure;
using Azure.Data.Tables;

public class ContainerInstanceMetadata : ITableEntity
{
    public string PartitionKey { get; set; }
    public string RowKey { get; set; }
    public string SubOrchestrationId { get; set; }
    public bool Processed { get; set; }
    public DateTimeOffset? Timestamp { get; set; }
    public ETag ETag { get; set; }
}
