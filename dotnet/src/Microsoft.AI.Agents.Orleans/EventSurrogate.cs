using Microsoft.AI.Agents.Abstractions;

namespace Microsoft.AI.Agents.Orleans;

[GenerateSerializer]
internal struct EventSurrogate
{
    [Id(0)]
    public string Namespace { get; set; }
    [Id(1)]
    public Dictionary<string, string> Data { get; set; }
    [Id(2)]
    public string Type { get; set; }
    [Id(3)]
    public string Subject { get; set; }
}

[RegisterConverter]
internal sealed class EventSurrogateConverter :
    IConverter<Event, EventSurrogate>
{
    public Event ConvertFromSurrogate(
        in EventSurrogate surrogate) =>
        new() { Namespace = surrogate.Namespace, Data = surrogate.Data, Subject = surrogate.Subject, Type = surrogate.Type };

    public EventSurrogate ConvertToSurrogate(
        in Event value) =>
        new()
        {
            Namespace = value.Namespace,
            Data = value.Data,
            Type = value.Type,
            Subject = value.Subject
        };
}
