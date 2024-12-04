// Copyright (c) Microsoft Corporation. All rights reserved.
// GroupChatBase.cs

using Microsoft.AspNetCore.Builder;
using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.AgentChat.Abstractions;
using Microsoft.AutoGen.Agents;
using Microsoft.AutoGen.Runtime;
using Microsoft.Extensions.DependencyInjection;
using TextMessage = Microsoft.AutoGen.AgentChat.Abstractions.TextMessage;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

internal class RuntimeScaffolding
{

}

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

    public async IAsyncEnumerable<TaskFrame> StreamAsync(string task, CancellationToken cancellationToken)
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
        //const string collectorAgentType = "collect_output_messages";

        Dictionary<string, Type> agentMap = new Dictionary<string, Type>();
        AgentChatConfigurator configurator = new AgentChatConfigurator(groupTopicType, outputTopicType);

        foreach (var participant in participants)
        {
            configurator[participant.Name] = new AgentChatConfig(participant, groupTopicType, outputTopicType);
            agentMap[participant.Name] = typeof(ChatAgentContainer); // We always host inside of ChatAgentContainer

            // TODO: Add topic subscriptions? (does not seem to do anything? see GrpcAgentWorker.RegisterAgentTypeAsync)
        }

        agentMap[groupChatManagerTopicType] = typeof(TManager);

        hostBuilder.Services.AddSingleton(configurator);

        // TODO: Where does the AgentRuntime come from?
        AgentTypes agentTypes = new AgentTypes(agentMap);

        await AgentsApp.StartAsync(hostBuilder, agentTypes, local: true);

        // TODO: Send this on
        _ = new GroupChatStart
        {
            Message = new TextMessage
            {
                Content = task,
                Source = "user"
            }
        };



        // TODO: Protos
        //AgentsApp.PublishMessageAsync(groupChatManagerTopicType, taskMessage);

    }
}
