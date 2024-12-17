// Copyright (c) Microsoft Corporation. All rights reserved.
// EventExtensions.cs

using System.Globalization;
using Microsoft.AutoGen.Contracts;

namespace DevTeam;

public static class EventExtensions
{
    public static GithubContext ToGithubContext(this Event evt)
    {
        ArgumentNullException.ThrowIfNull(evt);
        var data = new Dictionary<string, string>();// JsonSerializer.Deserialize<Dictionary<string,string>>(evt.Data);
        return new GithubContext
        {
            Org = data?["org"] ?? "",
            Repo = data?["repo"] ?? "",
            IssueNumber = data?.TryParseLong("issueNumber") ?? default,
            ParentNumber = data?.TryParseLong("parentNumber")
        };
    }

    public static Dictionary<string, string> ToData(this Event evt)
    {
        ArgumentNullException.ThrowIfNull(evt);
        return //JsonSerializer.Deserialize<Dictionary<string,string>>(evt.Data) ??
                new Dictionary<string, string>();
    }
    public static Dictionary<string, string> ToData(this GithubContext context)
    {
        ArgumentNullException.ThrowIfNull(context);

        return new Dictionary<string, string> {
            { "org", context.Org },
            { "repo", context.Repo },
            { "issueNumber", $"{context.IssueNumber}" },
            { "parentNumber", context.ParentNumber?.ToString(CultureInfo.InvariantCulture) ?? "" }
        };
    }
}

public class GithubContext
{
    public required string Org { get; set; }
    public required string Repo { get; set; }
    public long IssueNumber { get; set; }
    public long? ParentNumber { get; set; }

    public string Subject => $"{Org}/{Repo}/{IssueNumber}";
}
