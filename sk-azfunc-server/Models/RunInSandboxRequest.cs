namespace SK.DevTeam
{
    public class RunInSandboxRequest
    {
        public AddToPRRequest PrRequest { get; set; }
        public string SanboxOrchestrationId { get; set; }
    }
}