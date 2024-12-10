// Copyright (c) Microsoft Corporation. All rights reserved.
// Handoff.cs

namespace Microsoft.AutoGen.AgentChat.Abstractions;

public class Handoff(string target, string? description = null, string? name = null, string? message = null)
{
    private static string? CheckName(string? name)
    {
        if (name != null && !AgentName.IsValid(name))
        {
            throw new ArgumentException($"Handoff name '{name}' is not a valid identifier.");
        }

        return name;
    }

    public AgentName Target { get; } = new AgentName(target);
    public string Description { get; } = description ?? $"Handoff to {target}";
    public string Name { get; } = CheckName(name) ?? $"transfer_to_{target.ToLowerInvariant()}";
    public string Message { get; } = message ?? $"Transferred to {target}, adopting the role of {target} immediately.";

    private string DoHandoff() => this.Message;

    public ITool HandoffTool => new CallableTool(this.Name, this.Description, this.DoHandoff);
}
