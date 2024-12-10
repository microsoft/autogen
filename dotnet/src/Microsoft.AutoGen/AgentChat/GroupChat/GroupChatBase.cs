// Copyright (c) Microsoft Corporation. All rights reserved.
// GroupChatBase.cs

using System.Runtime.CompilerServices;
using Microsoft.AspNetCore.Builder;
using Microsoft.AutoGen.AgentChat.Abstractions;
using Microsoft.AutoGen.Agents;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using TextMessage = Microsoft.AutoGen.AgentChat.Abstractions.TextMessage;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

public abstract class GroupChatBase<TManager> : ITeam where TManager : GroupChatManagerBase
{
    private readonly List<IChatAgent> participants;
    private readonly List<AgentMessage> messageThread;
    private readonly ITerminationCondition? terminationCondition;

    public GroupChatBase(List<IChatAgent> participants, ITerminationCondition? terminationCondition = null)
    {
        this.participants = participants;
        this.messageThread = new List<AgentMessage>();
        this.terminationCondition = terminationCondition;

        this.TeamId = Guid.NewGuid();
    }

    public Guid TeamId
    {
        get;
        private set;
    }

    // TODO: Turn this into an IDisposable-based utility
    private int running; // = 0
    private bool EnsureSingleRun()
    {
        return Interlocked.CompareExchange(ref running, 1, 0) == 0;
    }

    private void EndRun()
    {
        this.running = 0;
    }

    public async IAsyncEnumerable<TaskFrame> StreamAsync(string task, [EnumeratorCancellation] CancellationToken cancellationToken)
    {
        if (String.IsNullOrEmpty(task))
        {
            throw new ArgumentNullException(nameof(task));
        }

        if (!this.EnsureSingleRun())
        {
            throw new InvalidOperationException("The task is already running.");
        }

        WebApplicationBuilder hostBuilder = WebApplication.CreateBuilder();

        // Inject relevant services

        // TODO: Where do these come from?
        const string groupTopicType = "group_topic";
        const string outputTopicType = "output_topic";
        const string groupChatManagerTopicType = "group_chat_manager";
        const string collectorAgentType = "collect_output_messages";

        Dictionary<string, Type> agentMap = new Dictionary<string, Type>();
        AgentChatBinder binder = new AgentChatBinder(groupTopicType, outputTopicType, cancellationToken);

        foreach (var participant in participants)
        {
            binder[participant.Name] = new AgentChatConfig(participant, groupTopicType, outputTopicType);
            agentMap[participant.Name] = typeof(ChatAgentContainer); // We always host inside of ChatAgentContainer
        }

        agentMap[groupChatManagerTopicType] = typeof(TManager);
        agentMap[collectorAgentType] = typeof(OutputCollectorAgent);

        hostBuilder.Services.AddSingleton(binder);
        
        AgentTypes agentTypes = new AgentTypes(agentMap);

        await AgentsApp.StartAsync(hostBuilder, agentTypes, local: true);

        // TODO: Send this on
        GroupChatStart taskStart = new()
        {
            Message = new TextMessage
            {
                Content = task,
                Source = "user"
            }
        };

        // TODO: Turn this into a less verbose helper call
        Task shutdownTask = AgentsApp.Host.WaitForShutdownAsync(cancellationToken);
        _ = shutdownTask.ContinueWith((t) =>
        {
            binder.OutputQueue.TryEnqueue(null);
        }, cancellationToken, TaskContinuationOptions.AttachedToParent, TaskScheduler.Current);

        try
        {
            // TODO: Protos
            GroupChatStart taskMessage = new GroupChatStart
            {
                Message = new TextMessage
                {
                    Content = task,
                    Source = "user"
                }
            };

            // TODO: Convert events to Protos so they can participate in the PublishMessageAsync contracts
            // Alternatively, don't force the events that we publish to be Protos (similar to Python?)
            //await AgentsApp.PublishMessageAsync(groupChatManagerTopicType, taskMessage.ToCloudEvt());

            List<AgentMessage> outputMessages = [];
            while (true)
            {
                AgentMessage? chatMessage = await binder.OutputQueue.DequeueAsync();
                // any of:
                //  * the queue was disposed,
                //  * we sent a null,
                //  * cancellation was requested
                if (chatMessage == null)
                {
                    break;
                }

                outputMessages.Add(chatMessage);
                yield return new TaskFrame(chatMessage);
            }

            TaskResult result = new TaskResult(outputMessages)
            {
                StopReason = binder.StopReason
            };

            yield return new TaskFrame(result);
        }
        finally
        {
            await shutdownTask;

            

            this.EndRun();
        }
    }

    public ValueTask ResetAsync(CancellationToken cancel)
    {
        throw new NotImplementedException();
    }
}
