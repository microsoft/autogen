public class IssueOrchestrationRequest
{
    public string Org { get; set; }
    public string Repo { get; set; }
    public long Number { get; set; }
    public string Input { get; set; }
    public string Branch => $"sk-{Number}";
}