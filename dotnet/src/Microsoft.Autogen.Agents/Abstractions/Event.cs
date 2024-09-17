using System.Runtime.Serialization;

namespace Microsoft.AI.Agents.Abstractions;

/// <summary>
/// Base class for all events
/// </summary>
[DataContract]
public class Event
{
    public required Dictionary<string, string> Data { get; set; }
    public required string Namespace { get; set; }
    public required string Type { get; set; }
    public string Subject { get; set; } = "";
}
