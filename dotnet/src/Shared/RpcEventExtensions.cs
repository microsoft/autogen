using System.Text.Json;
using Event = Microsoft.AI.Agents.Abstractions.Event;
using RpcEvent = Agents.Event;

namespace Microsoft.AI.Agents.Worker;

public static class RpcEventExtensions
{
    public static RpcEvent ToRpcEvent(this Event input)
    {
        var result = new RpcEvent
        {
            Namespace = input.Namespace,
            DataType = input.Type,
        };

        if (input.Data is not null)
        {
            result.Data = JsonSerializer.Serialize(input.Data);
        }

        return result;
    }

    public static Event ToEvent(this RpcEvent input)
    {
        var result = new Event
        {
            Type = input.DataType,
            Subject = input.Namespace,
            Namespace = input.Namespace,
            Data = []
        };

        if (input.Data is not null)
        {
            result.Data = JsonSerializer.Deserialize<Dictionary<string, string>>(input.Data)!;
        }

        return result;
    }
}
