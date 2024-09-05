using System.Text.Json;
using Event = Microsoft.AI.Agents.Abstractions.Event;
using RpcEvent = Agents.Event;
using Payload = Agents.Payload;
using Google.Protobuf;
using System.Text;

namespace Microsoft.AI.Agents.Worker;

public static class RpcEventExtensions
{
    public static RpcEvent ToRpcEvent(this Event input)
    {
        var result = new RpcEvent
        {
            TopicSource = input.Namespace,
            // TODO: Is this the right way to handle topics?
            TopicType = input.Subject
        };

        if (input.Data is not null)
        {
            result.Payload = new Payload
            {
                Data = ByteString.CopyFrom(JsonSerializer.Serialize(input.Data), Encoding.UTF8),
                DataContentType = "application/json",
                DataType = input.Type
            };
        }

        return result;
    }

    public static Event ToEvent(this RpcEvent input)
    {
        var result = new Event
        {
            Type = input.Payload.DataType,
            Subject = input.TopicType,
            Namespace = input.TopicSource,
            Data = []
        };

        if (input.Payload is not null)
        {
            if (input.Payload.DataContentType != "application/json")
            {
                throw new InvalidOperationException("Only application/json content type is supported");
            }

            result.Data = JsonSerializer.Deserialize<Dictionary<string, string>>(input.Payload.Data.ToString(Encoding.UTF8))!;
        }

        return result;
    }
}
