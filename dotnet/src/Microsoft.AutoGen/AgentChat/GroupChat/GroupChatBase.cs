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

    private readonly RuntimeLayer runtimeLayer;

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

        this.TeamId = Guid.NewGuid().ToString().ToLowerInvariant();

        this.runtimeLayer = new RuntimeLayer(this);
        this.RunManager = new(this.InitializationLayersInternal);
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
            }
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

    private sealed class RuntimeLayer(GroupChatBase<TManager> groupChat) : IRunContextLayer
    {
        public GroupChatBase<TManager> GroupChat { get; } = groupChat;
        public InProcessRuntime? Runtime { get; private set; }
        public OutputSink? OutputSink { get; private set; }

        public Task? InitOnceTask { get; set; }
        public Task ShutdownTask { get; set; } = Task.CompletedTask;

        public async ValueTask DeinitializeAsync()
        {
            await this.ShutdownTask;
        }

        private async Task CreateRuntime()
        {
            this.Runtime = new InProcessRuntime();

            foreach (AgentChatConfig config in this.GroupChat.Participants.Values)
            {
                await this.Runtime.RegisterChatAgentAsync(config);
            }

            await this.Runtime.RegisterGroupChatManagerAsync(this.GroupChat.GroupChatOptions, this.GroupChat.TeamId, this.GroupChat.CreateChatManager);

            this.OutputSink = new OutputSink();
            await this.Runtime.RegisterOutputCollectorAsync(this.OutputSink, this.GroupChat.GroupChatOptions.OutputTopicType);
        }

        public async ValueTask InitializeAsync()
        {
            if (this.InitOnceTask == null)
            {
                this.InitOnceTask = this.CreateRuntime();
            }

            await this.InitOnceTask;

            await this.Runtime!.StartAsync();
        }
    }

    private IRunContextLayer[] InitializationLayersInternal =>
        [
            this.runtimeLayer, ..this.InitializationLayers
        ];

    protected virtual IEnumerable<IRunContextLayer> InitializationLayers => [];

    private RunManager RunManager { get; }

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

    private InProcessRuntime? Runtime => this.runtimeLayer.Runtime;
    private OutputSink? OutputSink => this.runtimeLayer.OutputSink;

    private Task ShutdownTask
    {
        get => this.runtimeLayer.ShutdownTask;
        set => this.runtimeLayer.ShutdownTask = value;
    }

    private Func<CancellationToken, ValueTask> PrepareStream(ChatMessage task)
    {
        GroupChatStart taskMessage = new GroupChatStart
        {
            Messages = [task]
        };

        return async (CancellationToken cancellationToken) =>
        {
            AgentId chatManagerId = new AgentId(GroupChatManagerTopicType, this.TeamId);
            await this.Runtime!.SendMessageAsync(taskMessage, chatManagerId, cancellationToken: cancellationToken);
            this.ShutdownTask = Task.Run(this.Runtime!.RunUntilIdleAsync);
        };
    }

    private async IAsyncEnumerable<TaskFrame> StreamOutput([EnumeratorCancellation] CancellationToken cancellationToken)
    {
        List<AgentMessage> runMessages = new();

        while (true)
        {
            OutputSink.SinkFrame frame = await this.OutputSink!.WaitForDataAsync(cancellationToken);
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

    public IAsyncEnumerable<TaskFrame> StreamAsync(ChatMessage? task, CancellationToken cancellationToken = default)
    {
        if (task == null)
        {
            throw new ArgumentNullException(nameof(task));
        }

        const string TaskAlreadyRunning = "The task is already running";
        return this.RunManager.StreamAsync(
            this.StreamOutput,
            cancellationToken,
            this.PrepareStream(task),
            TaskAlreadyRunning);
    }

    private async ValueTask ResetInternalAsync(CancellationToken cancel)
    {
        try
        {
            foreach (var participant in this.Participants.Values)
            {
                await this.Runtime!.SendMessageAsync(
                    new GroupChatReset(),
                    new AgentId(participant.ParticipantTopicType, this.TeamId),
                    cancellationToken: cancel);
            }

            await this.Runtime!.SendMessageAsync(
                new GroupChatReset(),
                new AgentId(GroupChatManagerTopicType, this.TeamId),
                cancellationToken: cancel);

            await this.Runtime!.RunUntilIdleAsync();
        }
        finally
        {
            this.OutputSink?.Reset();
        }
    }

    public ValueTask ResetAsync(CancellationToken cancel)
    {
        const string TaskAlreadyRunning = "The group chat is currently running. It must be stopped before it can be reset.";
        return this.RunManager.RunAsync(
            this.ResetInternalAsync,
            cancel,
            message: TaskAlreadyRunning);
    }
}
