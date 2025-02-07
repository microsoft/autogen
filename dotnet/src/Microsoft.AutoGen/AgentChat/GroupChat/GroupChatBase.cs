// Copyright (c) Microsoft Corporation. All rights reserved.
// GroupChatBase.cs

using System.Diagnostics;
using System.Reflection;
using System.Runtime.CompilerServices;
using Microsoft.AutoGen.AgentChat.Abstractions;
using Microsoft.AutoGen.Contracts;
using Microsoft.AutoGen.Core;

namespace Microsoft.AutoGen.AgentChat.GroupChat;

internal static class AgentsRuntimeExtensions
{
    public static async ValueTask<AgentType> RegisterChatAgentAsync(this IAgentRuntime runtime, AgentChatConfig config)
    {
        AgentType type = config.Name;

        AgentType resultType = await runtime.RegisterAgentFactoryAsync(type,
            (id, runtime) =>
            {
                AgentInstantiationContext agentContext = new AgentInstantiationContext(id, runtime);
                return ValueTask.FromResult<IHostableAgent>(new ChatAgentRouter(agentContext, config));
            });

        await runtime.AddSubscriptionAsync(new TypeSubscription(config.ParticipantTopicType, type));
        await runtime.AddSubscriptionAsync(new TypeSubscription(config.ParentTopicType, type));

        return resultType;
    }

    public static async ValueTask<AgentType> RegisterGroupChatManagerAsync<TManager>(this IAgentRuntime runtime, GroupChatOptions options, string teamId, Func<GroupChatOptions, TManager> factory)
        where TManager : GroupChatManagerBase
    {
        AgentType type = GroupChatBase<TManager>.GroupChatManagerTopicType;
        AgentId expectedId = new AgentId(type, teamId);

        AgentType resultType = await runtime.RegisterAgentFactoryAsync(type,
            (id, runtime) =>
            {
                Debug.Assert(expectedId == id, $"Expecting the AgentId {expectedId} to be the teamId {id}");

                AgentInstantiationContext agentContext = new AgentInstantiationContext(id, runtime);
                TManager gcm = factory(options); // TODO: Should we allow this to be async?

                return ValueTask.FromResult<IHostableAgent>(new GroupChatHandlerRouter<TManager>(agentContext, gcm));
            });

        await runtime.AddSubscriptionAsync(new TypeSubscription(GroupChatBase<TManager>.GroupChatManagerTopicType, resultType));
        await runtime.AddSubscriptionAsync(new TypeSubscription(options.GroupChatTopicType, resultType));

        return resultType;
    }

    public static async ValueTask<AgentType> RegisterOutputCollectorAsync(this IAgentRuntime runtime, IOutputCollectionSink sink, string outputTopicType)
    {
        AgentType type = GroupChatBase<GroupChatManagerBase>.CollectorAgentType;
        AgentType resultType = await runtime.RegisterAgentFactoryAsync(type,
            (id, runtime) =>
            {
                AgentInstantiationContext agentContext = new AgentInstantiationContext(id, runtime);
                return ValueTask.FromResult<IHostableAgent>(new OutputCollectorAgent(agentContext, sink));
            });

        await runtime.AddSubscriptionAsync(new TypeSubscription(outputTopicType, type));

        return resultType;
    }
}

public abstract class GroupChatBase<TManager> : ITeam where TManager : GroupChatManagerBase
{
    // TODO: Where do these come from?
    internal const string GroupTopicType = "group_topic";
    internal const string OutputTopicType = "output_topic";
    internal const string GroupChatManagerTopicType = "group_chat_manager";
    internal const string CollectorAgentType = "collect_output_messages";

    private GroupChatOptions GroupChatOptions { get; }

    private readonly List<AgentMessage> messageThread = new();
    private Dictionary<string, AgentChatConfig> Participants { get; } = new();

    protected GroupChatBase(List<IChatAgent> participants, ITerminationCondition? terminationCondition = null, int? maxTurns = null)
    {
        this.GroupChatOptions = new GroupChatOptions(GroupTopicType, OutputTopicType)
        {
            TerminationCondition = terminationCondition,
            MaxTurns = maxTurns,
        };

        foreach (var participant in participants)
        {
            AgentChatConfig config = new AgentChatConfig(participant, GroupTopicType, OutputTopicType);
            this.Participants[participant.Name] = config;
            this.GroupChatOptions.Participants[participant.Name] = new GroupParticipant(config.ParticipantTopicType, participant.Description);
        }

        this.messageThread = new List<AgentMessage>(); // TODO: Allow injecting this

        this.TeamId = Guid.NewGuid().ToString().ToLowerInvariant();
    }

    public string TeamId
    {
        get;
        private set;
    }

    public virtual TManager CreateChatManager(GroupChatOptions options)
    {
        try
        {
            if (Activator.CreateInstance(typeof(TManager), options) is TManager result)
            {
                return result;
            };
        }
        catch (TargetInvocationException tie)
        {
            throw new Exception("Could not create chat manager", tie.InnerException);
        }
        catch (Exception ex)
        {
            throw new Exception("Could not create chat manager", ex);
        }

        throw new Exception("Could not create chat manager; make sure that it contains a ctor() or ctor(GroupChatOptions), or override the CreateChatManager method");
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

    public IAsyncEnumerable<TaskFrame> StreamAsync(string task, CancellationToken cancellationToken)
    {
        if (String.IsNullOrEmpty(task))
        {
            throw new ArgumentNullException(nameof(task));
        }

        // TODO: Send this on
        TextMessage taskStart = new()
        {
            Content = task,
            Source = "user"
        };

        return this.StreamAsync(taskStart, cancellationToken);
    }

    public ValueTask ResetAsync(CancellationToken cancel)
    {
        return ValueTask.CompletedTask;
    }

    public async IAsyncEnumerable<TaskFrame> StreamAsync(ChatMessage? task, [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        if (task == null)
        {
            throw new ArgumentNullException(nameof(task));
        }

        if (!this.EnsureSingleRun())
        {
            throw new InvalidOperationException("The task is already running.");
        }

        // TODO: How do we allow the user to configure this?
        //AgentsAppBuilder builder = new AgentsAppBuilder().UseInProcessRuntime();
        InProcessRuntime runtime = new InProcessRuntime();

        foreach (AgentChatConfig config in this.Participants.Values)
        {
            await runtime.RegisterChatAgentAsync(config);
        }

        await runtime.RegisterGroupChatManagerAsync(this.GroupChatOptions, this.TeamId, this.CreateChatManager);

        OutputSink outputSink = new OutputSink();
        await runtime.RegisterOutputCollectorAsync(outputSink, this.GroupChatOptions.OutputTopicType);

        await runtime.StartAsync();

        Task shutdownTask = Task.CompletedTask;

        try
        {
            // TODO: Protos
            GroupChatStart taskMessage = new GroupChatStart
            {
                Messages = [task]
            };

            List<AgentMessage> runMessages = new();

            AgentId chatManagerId = new AgentId(GroupChatManagerTopicType, this.TeamId);
            await runtime.SendMessageAsync(taskMessage, chatManagerId, cancellationToken: cancellationToken);

            shutdownTask = Task.Run(runtime.RunUntilIdleAsync);

            while (true)
            {
                OutputSink.SinkFrame frame = await outputSink.WaitForDataAsync(cancellationToken);
                runMessages.AddRange(frame.Messages);

                foreach (AgentMessage message in frame.Messages)
                {
                    yield return new TaskFrame(message);
                }

                if (frame.IsTerminal)
                {
                    TaskResult result = new TaskResult(runMessages);
                    yield return new TaskFrame(result);
                    break;
                }
            }
        }
        finally
        {
            this.EndRun();

            await shutdownTask;
        }
    }
}
