// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentTypes.cs
using Microsoft.AutoGen.Core;
namespace Microsoft.AutoGen.RuntimeGateway.Grpc.Tests;
public sealed class AgentTypes(Dictionary<string, Type> types)
{
    public Dictionary<string, Type> Types { get; } = types;
    public static AgentTypes? GetAgentTypesFromAssembly()
    {
        var agents = AppDomain.CurrentDomain.GetAssemblies()
                                .SelectMany(assembly => assembly.GetTypes())
                                .Where(type => ReflectionHelper.IsSubclassOfGeneric(type, typeof(BaseAgent))
                                    && !type.IsAbstract)
                                .ToDictionary(type => type.Name, type => type);

        return new AgentTypes(agents);
    }
}
