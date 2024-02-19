
[GenerateSerializer]
public class Event
{
    [Id(0)]
    public EventType Type { get; set; }
    [Id(1)]
    public string Message { get; set; }
    [Id(2)]
    public string Org { get; set; }
    [Id(3)]
    public string Repo { get; set; }
    [Id(4)]
    public long IssueNumber { get; set; }
}

public enum EventType
{
    NewAsk,
    NewAskReadme,
    NewAskPlan,
    NewAskImplement,
    ChainClosed,
    ReadmeCreated,
    PlanSubstepCreated,
    CodeCreated
}