namespace Microsoft.AI.Agents.Abstractions
{
    public class Event
    {
        public string Message { get; set; }
        public Dictionary<string, string> Data { get; set; }
        public string Type { get; set; }
    }
}