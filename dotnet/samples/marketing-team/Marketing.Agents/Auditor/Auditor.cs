// Copyright (c) Microsoft Corporation. All rights reserved.
// Auditor.cs

using Marketing.Shared;
using Microsoft.AutoGen.Abstractions;
using Microsoft.AutoGen.Agents;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Memory;

namespace Marketing.Agents;

[TopicSubscription("default")]
public class Auditor(IAgentContext context, Kernel kernel, ISemanticTextMemory memory, [FromKeyedServices("EventTypes")] EventTypes typeRegistry, ILogger<Auditor> logger)
    : SKAiAgent<AuditorState>(context, memory, kernel, typeRegistry),
    IHandle<AuditText>
{
    public async Task Handle(AuditText item)
    {
        logger.LogInformation($"[{nameof(Auditor)}] Event {nameof(AuditText)}. Text: {{Text}}", item.Text);

        var context = new KernelArguments { ["input"] = AppendChatHistory(item.Text) };
        var auditorAnswer = await CallFunction(AuditorPrompts.AuditText, context);
        if (auditorAnswer.Contains("NOTFORME", StringComparison.InvariantCultureIgnoreCase))
        {
            return;
        }

        await SendAuditorAlertEvent(auditorAnswer, item.UserId);
    }

    private async Task SendAuditorAlertEvent(string auditorAlertMessage, string userId)
    {
        var auditorAlert = new AuditorAlert
        {
            AuditorAlertMessage = auditorAlertMessage,
            UserId = userId
        }.ToCloudEvent(this.AgentId.Key);

        await PublishEvent(auditorAlert);
    }
}
