using Microsoft.AI.Agents.Abstractions;
using Microsoft.AI.DevTeam.Events;
using Orleans.Streams;

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

    public override async Task HandleEvent(Event item, StreamSequenceToken? token)
    {
        switch (item.Type)
        {
            case nameof(GithubFlowEventType.ReadmeCreated):
            {
                var parentNumber = long.Parse(item.Data["parentNumber"]);
                var issueNumber = long.Parse(item.Data["issueNumber"]);
                await Store(item.Data["org"], item.Data["repo"], parentNumber, issueNumber, "readme", "md", "output", item.Message);
                await PublishEvent(Consts.MainNamespace, this.GetPrimaryKeyString(), new Event
                {
                    Type = nameof(GithubFlowEventType.ReadmeStored),
                    Data = new Dictionary<string, string> {
                            { "org", item.Data["org"] },
                            { "repo", item.Data["repo"] },
                            { "issueNumber", item.Data["issueNumber"] },
                            { "parentNumber", item.Data["parentNumber"]  }
                        }
                });
            }
                
                break;
            case nameof(GithubFlowEventType.CodeCreated):
            {
                var parentNumber = long.Parse(item.Data["parentNumber"]);
                var issueNumber = long.Parse(item.Data["issueNumber"]);
                await Store(item.Data["org"], item.Data["repo"], parentNumber, issueNumber, "run", "sh", "output", item.Message);
                await RunInSandbox(item.Data["org"], item.Data["repo"], parentNumber, issueNumber);
                await PublishEvent(Consts.MainNamespace, this.GetPrimaryKeyString(), new Event
                {
                    Type = nameof(GithubFlowEventType.SandboxRunCreated),
                    Data = new Dictionary<string, string> {
                            { "org", item.Data["org"] },
                            { "repo", item.Data["repo"] },
                            { "issueNumber", item.Data["issueNumber"] },
                            { "parentNumber", item.Data["parentNumber"]  }
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