using Microsoft.AI.Agents.Abstractions;
using Microsoft.AI.DevTeam.Extensions;
using System.Globalization;

namespace Microsoft.AI.DevTeam.Events
{
    public enum GithubFlowEventType
    {
        NewAsk,
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
        SandboxRunFinished,
        ReadmeCreated,
        CodeCreated,
        DevPlanCreated,
        SandboxRunCreated
    }

    public static class EventExtensions
    {
        public static GithubContext ToGithubContext(this Event evt)
        {
            ArgumentNullException.ThrowIfNull(evt);

            return new GithubContext
            {
                Org = evt.Data["org"],
                Repo = evt.Data["repo"],
                IssueNumber = evt.Data.TryParseLong("issueNumber"),
                ParentNumber = evt.Data.TryParseLong("parentNumber")
            };
        }

        public static Dictionary<string, string> ToData(this GithubContext context)
        {
            ArgumentNullException.ThrowIfNull(context);

            return new Dictionary<string, string> {
                { "org", context.Org },
                { "repo", context.Repo },
                { "issueNumber", $"{context.IssueNumber}" },
                { "parentNumber", context.ParentNumber.HasValue ? Convert.ToString(context.ParentNumber, CultureInfo.InvariantCulture) : string.Empty }
            };
        }
    }

    public class GithubContext
    {
        public string Org { get; set; }
        public string Repo { get; set; }
        public long IssueNumber { get; set; }
        public long? ParentNumber { get; set; }

        public string Subject => $"{Org}/{Repo}/{IssueNumber}";
    }
}


