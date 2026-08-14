// Copyright (c) Microsoft Corporation. All rights reserved.
// AzureGenie.cs

using DevTeam.Backend.Services;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;

namespace DevTeam.Backend.Agents;

[TopicSubscription(Consts.TopicName)]
public class AzureGenie([FromKeyedServices("AgentsMetadata")] AgentsMetadata typeRegistry, IManageAzure azureService)
    : Agent(typeRegistry),
    IHandle<ReadmeCreated>,
    IHandle<CodeCreated>
{
    public async Task Handle(ReadmeCreated item, CancellationToken cancellationToken = default)
    {
        // TODO: Not sure we need to store the files if we use ACA Sessions
        //                //var data = item.ToData();
        //               // await Store(data["org"], data["repo"],  data.TryParseLong("parentNumber"),  data.TryParseLong("issueNumber"), "readme", "md", "output", data["readme"]);
        //                await PublishEventAsync(new Event
        //                {
        //                    Namespace = item.Namespace,
        //                    Type = nameof(EventTypes.ReadmeStored),
        //                    Data = item.Data
        //                });
        //                break;
        await Task.CompletedTask;
    }

    public async Task Handle(CodeCreated item, CancellationToken cancellationToken = default)
    {
        // TODO: Not sure we need to store the files if we use ACA Sessions
        //                //var data = item.ToData();
        //               // await Store(data["org"], data["repo"],  data.TryParseLong("parentNumber"),  data.TryParseLong("issueNumber"), "run", "sh", "output", data["code"]);
        //               // await RunInSandbox(data["org"], data["repo"],  data.TryParseLong("parentNumber"),  data.TryParseLong("issueNumber"));
        //                await PublishEventAsync(new Event
        //                {
        //                    Namespace = item.Namespace,
        //                    Type = nameof(EventTypes.SandboxRunCreated),
        //                    Data = item.Data
        //                });
        //                break;
        await Task.CompletedTask;
    }
    public async Task Store(string org, string repo, long parentIssueNumber, long issueNumber, string filename, string extension, string dir, string output)
    {
        await azureService.Store(org, repo, parentIssueNumber, issueNumber, filename, extension, dir, output);
    }

    public async Task RunInSandbox(string org, string repo, long parentIssueNumber, long issueNumber)
    {
        await azureService.RunInSandbox(org, repo, parentIssueNumber, issueNumber);
    }
}
