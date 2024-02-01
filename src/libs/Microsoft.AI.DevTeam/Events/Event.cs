public class Event
{
    public EventType Type { get; set; }
    public string Message { get; set; }
    public string Org { get; set; }
    public string Repo { get; set; }
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