using Microsoft.AI.Agents.Abstractions;
using Microsoft.AI.Agents.Orleans;
using Microsoft.AI.DevTeam.Events;
using Newtonsoft.Json.Linq;

namespace Microsoft.AI.DevTeam;

[ImplicitStreamSubscription(Consts.MainNamespace)]
public class AzureGenie : Agent
{
    protected override string Namespace => Consts.MainNamespace;
    private readonly IManageAzure _azureService;

    public AzureGenie( IManageAzure azureService)
    {
        _azureService = azureService;
    }

    public override async Task HandleEvent(Event item)
    {
        switch (item.Type)
        {
            case nameof(GithubFlowEventType.ReadmeCreated):
            {
                var data = item.Data;
                var parentNumber = long.Parse(data["parentNumber"].ToString());
                var issueNumber = long.Parse(data["issueNumber"].ToString());
                var org = data["org"].ToString();
                var repo = data["repo"].ToString();
                var subject = $"{org}/{repo}/{issueNumber}";
                await Store(org,repo, parentNumber, issueNumber, "readme", "md", "output", data["readme"].ToString());
                await PublishEvent(Consts.MainNamespace, this.GetPrimaryKeyString(), new Event
                {
                    Type = nameof(GithubFlowEventType.ReadmeStored),
                    Subject = subject,
                    Data = new Dictionary<string, string> {
                            { "org", org },
                            { "repo", repo },
                            { "issueNumber", $"{issueNumber}" },
                            { "parentNumber", $"{parentNumber}" }
                        }
                });
            }
                
                break;
            case nameof(GithubFlowEventType.CodeCreated):
            {
                var data = item.Data;
                var parentNumber = long.Parse(data["parentNumber"].ToString());
                var issueNumber = long.Parse(data["issueNumber"].ToString());
                var org = data["org"].ToString();
                var repo = data["repo"].ToString();
                var subject = $"{org}/{repo}/{issueNumber}";
                await Store(org,repo, parentNumber, issueNumber, "run", "sh", "output", data["code"].ToString());
                await RunInSandbox(org, repo, parentNumber, issueNumber);
                await PublishEvent(Consts.MainNamespace, this.GetPrimaryKeyString(), new Event
                {
                    Type = nameof(GithubFlowEventType.SandboxRunCreated),
                    Subject = subject,
                    Data = new Dictionary<string, string> {
                            { "org", org },
                            { "repo", repo },
                            { "issueNumber", $"{issueNumber}" },
                            { "parentNumber", $"{parentNumber}" }
                        }
                });
            }
                
                break;
            default:
                break;
        }
    }

    public async Task Store(string org, string repo, long parentIssueNumber, long issueNumber, string filename, string extension, string dir, string output)
    {
        await _azureService.Store(org, repo, parentIssueNumber, issueNumber, filename, extension, dir, output);
    }

    public async Task RunInSandbox(string org, string repo, long parentIssueNumber, long issueNumber)
    {
        await _azureService.RunInSandbox(org, repo, parentIssueNumber, issueNumber);
    }
}