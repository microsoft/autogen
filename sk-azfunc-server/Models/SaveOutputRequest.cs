namespace SK.DevTeam
{
    public class SaveOutputRequest
    {
        public string IssueOrchestrationId { get; set; }
        public string SubOrchestrationId { get; set; }
        public string Output { get; set; }
        public string Extension { get; set; }
        public string Directory { get; set; }
        public string FileName { get; set; }
    }
}
