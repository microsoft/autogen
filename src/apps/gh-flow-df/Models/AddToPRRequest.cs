public class AddToPRRequest
{
    public string Output { get; set; }
    public string IssueOrchestrationId { get; set; }
    public string SubOrchestrationId { get; set; }
    public string PrSubOrchestrationId { get; set; }
    public string Extension { get; set; }
    public bool RunInSandbox { get; set; }
    public IssueOrchestrationRequest Request { get; set; }
}
