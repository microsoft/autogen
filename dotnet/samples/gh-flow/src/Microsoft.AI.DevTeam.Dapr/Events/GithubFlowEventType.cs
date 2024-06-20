using System.Globalization;
using System.Runtime.Serialization;
using System.Text.Json.Serialization;
using Microsoft.AI.Agents.Abstractions;

namespace Microsoft.AI.DevTeam.Dapr.Events;

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
            IssueNumber = long.Parse(evt.Data["issueNumber"]),
            ParentNumber = string.IsNullOrEmpty(evt.Data["parentNumber"]) ? default : long.Parse(evt.Data["parentNumber"])
        };
    }

    public static Dictionary<string, string> ToData(this GithubContext context)
    {
        ArgumentNullException.ThrowIfNull(context);
        return new Dictionary<string, string> {
                        { "org", context.Org },
                        { "repo", context.Repo },
                        { "issueNumber", $"{context.IssueNumber}" },
                        { "parentNumber", context.ParentNumber?.ToString(CultureInfo.InvariantCulture) ?? ""}
        };
    }

}

public class GithubContext
{
    public required string Org { get; set; }
    public required string Repo { get; set; }
    public long IssueNumber { get; set; }
    public long? ParentNumber { get; set; }

    public string Subject => $"{Org}-{Repo}-{IssueNumber}";
}

[DataContract]
public class EventEnvelope
{
    [JsonPropertyName("data")]
    public required Event Data { get; set; }
}
