// Copyright (c) Microsoft Corporation. All rights reserved.
// Handoff.cs

namespace Microsoft.AutoGen.AgentChat.Abstractions;

/// <summary>
/// Handoff configuration.
/// </summary>
/// <param name="target">The name of the target agent receiving the handoff.</param>
/// <param name="description">The description of the handoff such as the condition under which it should happen and the target
/// agent's ability. If not provided, it is generated from the target agent's name.</param>
/// <param name="name">The name of this handoff configuration. If not provided, it is generated from the target agent's name.</param>
/// <param name="message">The message to the target agent. If not provided, it is generated from the target agent's name.</param>
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

    /// <summary>
    /// The name of the target agent receiving the handoff.
    /// </summary>
    public AgentName Target { get; } = new AgentName(target);

    /// <summary>
    /// The description of the handoff such as the condition under which it should happen and the target.
    /// </summary>
    public string Description { get; } = description ?? $"Handoff to {target}";

    /// <summary>
    /// The name of this handoff configuration.
    /// </summary>
    public string Name { get; } = CheckName(name) ?? $"transfer_to_{target.ToLowerInvariant()}";

    /// <summary>
    /// The content of the HandoffMessage that will be sent.
    /// </summary>
    public string Message { get; } = message ?? $"Transferred to {target}, adopting the role of {target} immediately.";

    /// <summary>
    /// Handoff Tool to execute the handoff.
    /// </summary>
    public ITool HandoffTool => new CallableTool(this.Name, this.Description, () => { return this.Message; });
}
