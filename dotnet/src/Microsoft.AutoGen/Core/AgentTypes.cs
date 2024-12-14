// Copyright (c) Microsoft Corporation. All rights reserved.
// AgentTypes.cs

namespace Microsoft.AutoGen.Core
;
public sealed class AgentTypes(Dictionary<string, Type> types)
{
    public Dictionary<string, Type> Types { get; } = types;
    public static AgentTypes? GetAgentTypesFromAssembly()
    {
        var agents = AppDomain.CurrentDomain.GetAssemblies()
                                .SelectMany(assembly => assembly.GetTypes())
                                .Where(type => ReflectionHelper.IsSubclassOfGeneric(type, typeof(Agent))
                                    && !type.IsAbstract
                                    && !type.Name.Equals(nameof(Client)))
                                .ToDictionary(type => type.Name, type => type);

        return new AgentTypes(agents);
    }
}
