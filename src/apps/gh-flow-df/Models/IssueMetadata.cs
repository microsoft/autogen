using Azure;
using Azure.Data.Tables;

public class IssueMetadata : ITableEntity
{
    public long? Number { get; set; }
    public int? CommentId { get; set; }

    public string? InstanceId { get; set; }

    public string? Id { get; set; }

    public string? Org { get; set; }
    public string? Repo { get; set; }
    public string PartitionKey { get; set; }
    public string RowKey { get; set; }
    public DateTimeOffset? Timestamp { get; set; }
    public ETag ETag { get; set; }
}
