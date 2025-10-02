// Copyright (c) Microsoft Corporation. All rights reserved.
// ToolManager.cs

using Microsoft.AutoGen.AgentChat.Abstractions;
using Microsoft.Extensions.AI;

namespace Microsoft.AutoGen.AgentChat.Agents;

internal sealed class ToolManager
{
    public Dictionary<string, ITool> Tools { get; } = new Dictionary<string, ITool>();
    public HashSet<string> Handoffs { get; init; }

    /// <summary>
    /// Initializes a new instance of the <see cref="ToolManager"/> class.
    /// </summary>
    /// <param name="tools">The tools to register.</param>
    /// <param name="handoffs">The handoff configurations to enable.</param>
    /// <exception cref="ArgumentException">
    /// Thrown when a tool or handoff name is not unique (including when a handoff name is the same as a tool name).
    /// </exception>
    public ToolManager(IEnumerable<ITool> tools, IEnumerable<Handoff> handoffs)
    {
        this.Tools = ToolManager.PrepareTools(tools, handoffs, out var handoffNames);
        this.Handoffs = handoffNames;
    }

    /// <summary>
    /// Prepares the tools and handoffs for use. Checks for uniqueness, projects the handoffs as tools, returns the
    /// combined tool set, and outputs the set of handoff names.
    /// </summary>
    /// <param name="tools">The tools to prepare. Tool names must be unique.</param>
    /// <param name="handoffs">
    /// The handoff configurations to prepare. Handoff names must be unique and must be unique from tool names.
    /// </param>
    /// <param name="handoffNames">
    /// Outputs the set of handoff names.
    /// </param>
    /// <returns>
    /// A dictionary of tools and handoffs, keyed by their names, and the set of handoff names.
    /// </returns>
    /// <exception cref="ArgumentException">Thrown when a tool or handoff name is not unique (including when a handoff
    /// name is the same as a tool name). </exception>
    private static Dictionary<string, ITool> PrepareTools(IEnumerable<ITool>? tools, IEnumerable<Handoff>? handoffs, out HashSet<string> handoffNames)
    {
        Dictionary<string, ITool> result = new Dictionary<string, ITool>();
        handoffNames = [];

        foreach (ITool tool in tools ?? [])
        {
            if (result.ContainsKey(tool.Name))
            {
                throw new ArgumentException($"Tool names must be unique. Duplicate tool name: {tool.Name}");
            }

            result[tool.Name] = tool;
        }

        foreach (Handoff handoff in handoffs ?? [])
        {
            if (handoffNames.Contains(handoff.Name))
            {
                throw new ArgumentException($"Handoff names must be unique. Duplicate handoff name: {handoff.Name}");
            }

            if (result.ContainsKey(handoff.Name))
            {
                throw new ArgumentException($"Handoff names must be unique from tool names. Duplicate handoff name: {handoff.Name}");
            }

            result[handoff.Name] = handoff.HandoffTool;
            handoffNames.Add(handoff.Name);
        }

        return result;
    }

    /// <summary>
    /// A helper method to look up a tool requested by the <see cref="FunctionCallContent"/> object,
    /// maps the arguments to the tool's parameters, and invokes the tool.
    /// </summary>
    /// <param name="functionCall">The function call to invoke.</param>
    /// <param name="cancellationToken">The <see cref="CancellationToken"/> to observe.</param>
    /// <returns>
    /// The result of the tool invocation.
    /// </returns>
    /// <exception cref="InvalidOperationException">
    /// Thrown when no tools are available.
    /// </exception>
    /// <exception cref="ArgumentException">
    /// Thrown when the tool requested is unknown or when a required parameter is missing.
    /// </exception>
    public async Task<FunctionResultContent> InvokeToolAsync(FunctionCallContent functionCall, CancellationToken cancellationToken)
    {
        if (this.Tools.Count == 0)
        {
            throw new InvalidOperationException("No tools available.");
        }

        ITool? targetTool = this.Tools.GetValueOrDefault(functionCall.Name)
                            ?? throw new ArgumentException($"Unknown tool: {functionCall.Name}");

        List<object?> parameters = new List<object?>();
        if (functionCall.Arguments != null)
        {
            foreach (var parameter in targetTool.Parameters)
            {
                if (!functionCall.Arguments!.TryGetValue(parameter.Name, out object? o))
                {
                    if (parameter.IsRequired)
                    {
                        throw new ArgumentException($"Missing required parameter: {parameter.Name}");
                    }
                    else
                    {
                        o = parameter.DefaultValue;
                    }
                }

                parameters.Add(o);
            }
        }

        try
        {
            // TODO: Nullability constraint on the tool execution is bad
            object callResult = await targetTool.ExecuteAsync((IEnumerable<object>)parameters, cancellationToken);
            //string serializedResult = JsonSerializer.Serialize(callResult);

            return new FunctionResultContent(functionCall.CallId, functionCall.Name, callResult);
        }
        catch (Exception e)
        {
            return new FunctionResultContent(functionCall.CallId, functionCall.Name, $"Error: {e}");
        }
    }

}
