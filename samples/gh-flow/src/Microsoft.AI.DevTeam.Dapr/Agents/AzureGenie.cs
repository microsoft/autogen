using Dapr.Actors;
using Dapr.Actors.Runtime;
using Dapr.Client;
using Microsoft.AI.Agents.Abstractions;
using Microsoft.AI.Agents.Dapr;
using Microsoft.AI.DevTeam.Dapr.Events;

namespace Microsoft.AI.DevTeam.Dapr;

public class AzureGenie : Agent, IDaprAgent
{
    private readonly IManageAzure _azureService;

    public AzureGenie(ActorHost host,DaprClient client, IManageAzure azureService) : base(host, client)
    {
        _azureService = azureService;
    }

    public override async Task HandleEvent(Event item)
    {
        switch (item.Type)
        {
            case nameof(GithubFlowEventType.ReadmeCreated):
            {
                var context = item.ToGithubContext();
                await Store(context.Org,context.Repo, context.ParentNumber.Value, context.IssueNumber, "readme", "md", "output", item.Data["readme"]);
                await PublishEvent(Consts.PubSub, Consts.MainTopic, new Event
                {
                    Type = nameof(GithubFlowEventType.ReadmeStored),
                    Subject = context.Subject,
                    Data = context.ToData()
                });
            }
                
                break;
            case nameof(GithubFlowEventType.CodeCreated):
            {
                var context = item.ToGithubContext();
                await Store(context.Org,context.Repo, context.ParentNumber.Value, context.IssueNumber, "run", "sh", "output", item.Data["code"]);
                await RunInSandbox(context.Org,context.Repo, context.ParentNumber.Value, context.IssueNumber);
                await PublishEvent(Consts.PubSub, Consts.MainTopic, new Event
                {
                    Type = nameof(GithubFlowEventType.SandboxRunCreated),
                    Subject = context.Subject,
                    Data = context.ToData()
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
