// Copyright (c) Microsoft Corporation. All rights reserved.
// GroupChat.cs

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;

namespace AutoGen;

public class GroupChat : IGroupChat
{
    private IAgent admin;
    private List<IAgent> agents = new List<IAgent>();
    private IEnumerable<Message> initializeMessages = new List<Message>();
    private Workflow? workflow = null;

    public IEnumerable<Message>? Messages { get; private set; }

    /// <summary>
    /// Create a group chat.
    /// </summary>
    /// <param name="admin">admin agent.</param>
    /// <param name="members">other members.</param>
    /// <param name="initializeMessages"></param>
    public GroupChat(
        IAgent admin,
        IEnumerable<IAgent> members,
        IEnumerable<Message>? initializeMessages = null,
        Workflow? workflow = null)
    {
        this.admin = admin;
        this.agents = members.ToList();
        this.agents.Add(admin);
        this.initializeMessages = initializeMessages ?? new List<Message>();
        this.workflow = workflow;

        this.Validation();
    }

    private void Validation()
    {
        // check if all agents has a name
        if (this.agents.Any(x => string.IsNullOrEmpty(x.Name)))
        {
            throw new Exception("All agents must have a name.");
        }

        // check if any agents has the same name
        var names = this.agents.Select(x => x.Name).ToList();
        if (names.Distinct().Count() != names.Count)
        {
            throw new Exception("All agents must have a unique name.");
        }

        // if there's a workflow
        // check if the agents in that workflow are in the group chat
        if (this.workflow != null)
        {
            var agentNamesInWorkflow = this.workflow.Transitions.Select(x => x.From.Name!).Concat(this.workflow.Transitions.Select(x => x.To.Name!)).Distinct();
            if (agentNamesInWorkflow.Any(x => !this.agents.Select(a => a.Name).Contains(x)))
            {
                throw new Exception("All agents in the workflow must be in the group chat.");
            }
        }
    }

    public async Task<IAgent?> SelectNextSpeakerAsync(IAgent currentSpeaker, IEnumerable<Message> conversationHistory)
    {

        var agentNames = this.agents.Select(x => x.Name).ToList();
        if (this.workflow != null)
        {
            var nextAvailableAgents = await this.workflow.TransitToNextAvailableAgentsAsync(currentSpeaker, conversationHistory);
            agentNames = nextAvailableAgents.Select(x => x.Name).ToList();
            if (agentNames.Count() == 0)
            {
                throw new Exception("No next available agents found in the current workflow");
            }

            if (agentNames.Count() == 1)
            {
                return this.agents.FirstOrDefault(x => x.Name == agentNames.First());
            }
        }
        var systemMessage = new Message(Role.System,
            content: $@"You are in a role play game. Carefully read the conversation history and carry on the conversation.
The available roles are:
{string.Join(",", agentNames)}

Each message will start with 'From name:', e.g:
From admin:
//your message//.");

        var conv = this.ProcessConversationsForRolePlay(this.initializeMessages, conversationHistory);

        var messages = new Message[] { systemMessage }.Concat(conv);
        var response = await this.admin.GenerateReplyAsync(
            messages: messages,
            options: new GenerateReplyOptions
            {
                Temperature = 0,
                MaxToken = 128,
                StopSequence = [":"],
                Functions = [],
            });

        var name = response?.Content ?? throw new Exception("No name is returned.");

        try
        {
            // remove From
            name = name!.Substring(5);
            var agent = this.agents.FirstOrDefault(x => x.Name!.ToLower() == name.ToLower());

            return agent;
        }
        catch (Exception)
        {
            return null;
        }
    }

    public void AddInitializeMessage(Message message)
    {
        this.initializeMessages = this.initializeMessages.Append(message);
    }

    public async Task<IEnumerable<Message>> CallAsync(
        IEnumerable<Message>? conversationWithName = null,
        int maxRound = 10,
        CancellationToken ct = default)
    {
        var conversationHistory = new List<Message>();
        if (conversationWithName != null)
        {
            conversationHistory.AddRange(conversationWithName);
        }

        var lastSpeaker = conversationHistory.LastOrDefault()?.From switch
        {
            null => this.agents.First(),
            _ => this.agents.FirstOrDefault(x => x.Name == conversationHistory.Last().From) ?? throw new Exception("The agent is not in the group chat"),
        };
        var round = 0;
        while (round < maxRound)
        {
            var currentSpeaker = await this.SelectNextSpeakerAsync(lastSpeaker, conversationHistory) ?? this.admin;
            var processedConversation = this.ProcessConversationForAgent(this.initializeMessages, conversationHistory);
            var result = await currentSpeaker.GenerateReplyAsync(processedConversation) ?? throw new Exception("No result is returned.");
            conversationHistory.Add(result);

            // if message is terminate message, then terminate the conversation
            if (result?.IsGroupChatTerminateMessage() ?? false)
            {
                break;
            }

            lastSpeaker = currentSpeaker;
            round++;
        }

        return conversationHistory;
    }
}
