using Microsoft.AI.Agents.Abstractions;

namespace Microsoft.AI.Agents.Orleans;

[GenerateSerializer]
public struct EventSurrogate
{
    [Id(0)]
    public Dictionary<string, string> Data { get; set; }
    [Id(1)]
    public string Type { get; set; }
    [Id(2)]
    public string Subject { get; set; }
}

[RegisterConverter]
public sealed class EventSurrogateConverter :
    IConverter<Event, EventSurrogate>
{
    public Event ConvertFromSurrogate(
        in EventSurrogate surrogate) =>
        new Event { Data = surrogate.Data, Subject = surrogate.Subject, Type = surrogate.Type};

    public EventSurrogate ConvertToSurrogate(
        in Event value) =>
        new EventSurrogate
        {
            Data = value.Data,
            Type = value.Type,
            Subject = value.Subject
        };
}
