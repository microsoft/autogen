using Microsoft.AI.Agents.Abstractions;
using Microsoft.AI.Agents.Orleans;
using Microsoft.AI.DevTeam.Events;
using Microsoft.AI.DevTeam.Extensions;

namespace Microsoft.AI.DevTeam;

[ImplicitStreamSubscription(Consts.MainNamespace)]
public class AzureGenie : Agent
{
    protected override string Namespace => Consts.MainNamespace;
    private readonly IManageAzure _azureService;

    public AzureGenie(IManageAzure azureService)
    {
        _azureService = azureService;
    }

    public override async Task HandleEvent(Event item)
    {
        if (item?.Type is null)
        {
            throw new ArgumentNullException(nameof(item));
        }

        switch (item.Type)
        {
            case nameof(GithubFlowEventType.ReadmeCreated):
            {
                 var context = item.ToGithubContext();
                await Store(context.Org,context.Repo, context.ParentNumber.Value, context.IssueNumber, "readme", "md", "output", item.Data["readme"]);
                await PublishEvent(Consts.MainNamespace, this.GetPrimaryKeyString(), new Event
                {
                    Type = nameof(GithubFlowEventType.ReadmeStored),
                    Subject = context.Subject,
                    Data = context.ToData()
                });
                 break;
            }
               
               
            case nameof(GithubFlowEventType.CodeCreated):
            {
                var context = item.ToGithubContext();
                await Store(context.Org,context.Repo, context.ParentNumber.Value, context.IssueNumber, "run", "sh", "output", item.Data["code"]);
                await RunInSandbox(context.Org,context.Repo, context.ParentNumber.Value, context.IssueNumber);
                await PublishEvent(Consts.MainNamespace, this.GetPrimaryKeyString(), new Event
                {
                    Type = nameof(GithubFlowEventType.SandboxRunCreated),
                    Subject = context.Subject,
                    Data = context.ToData()
                });
                  break;
            }

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