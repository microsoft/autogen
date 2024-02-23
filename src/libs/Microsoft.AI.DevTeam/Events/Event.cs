
[GenerateSerializer]
public class Event
{
    [Id(0)]
    public EventType Type { get; set; }
    [Id(1)]
    public string Message { get; set; }
    [Id(2)]
    public Dictionary<string,string> Data { get; set; }
}

public enum EventType
{
    NewAsk,
    ChainClosed,
    ReadmeChainClosed,
    CodeChainClosed,
    CodeGenerationRequested,
    DevPlanRequested,
    ReadmeGenerated,
    DevPlanGenerated,
    CodeGenerated,
    DevPlanChainClosed,
    ReadmeRequested,
    ReadmeStored,
    SandboxRunFinished
}