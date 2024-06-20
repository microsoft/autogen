using System.Runtime.Serialization;

namespace Microsoft.AI.Agents.Abstractions;

[DataContract]
public class Event
{
    public required Dictionary<string, string> Data { get; set; }
    public required string Type { get; set; }
    public string Subject { get; set; } = "";
}
