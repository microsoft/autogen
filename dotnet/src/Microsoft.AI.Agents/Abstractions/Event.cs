using System.Runtime.Serialization;

namespace Microsoft.AI.Agents.Abstractions
{
    [DataContract]
    public class Event
    {
        public Dictionary<string, string> Data { get; set; }
        public string Type { get; set; }
        public string Subject { get; set; }
    }
}