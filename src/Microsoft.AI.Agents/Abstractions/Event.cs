using Orleans;
using Orleans.CodeGeneration;

namespace Microsoft.AI.Agents.Abstractions
{
    [GenerateSerializer]
    public class Event
    {
        [Id(0)]
        public string Message { get; set; }
        [Id(1)]
        public Dictionary<string, string> Data { get; set; }
        [Id(2)]
        public string Type { get; set; }
    }
}