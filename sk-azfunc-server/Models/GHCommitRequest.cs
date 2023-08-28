namespace SK.DevTeam
{
    public class GHCommitRequest
    {
        public object IssueOrchestrationId { get; set; }
        public object SubOrchestrationId { get; set; }
        public string Org { get; set; }
        public string Repo { get; set; }
        public object Directory { get; set; }
        public string Branch { get; set; }
    }
}