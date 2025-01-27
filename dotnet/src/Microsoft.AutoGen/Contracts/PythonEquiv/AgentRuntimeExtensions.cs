// Copyright (c) Microsoft Corporation. All rights reserved.
// PythonInterfaces.cs

using Microsoft.Extensions.DependencyInjection;

namespace Microsoft.AutoGen.Contracts.Python;

public static class AgentRuntimeExtensions
{
    internal static ValueTask<TAgent> ActivateAgentAsync<TAgent>(IServiceProvider serviceProvider, params object[] additionalArguments) where TAgent : IHostableAgent
    {
        try
        {
            var agent = (TAgent)ActivatorUtilities.CreateInstance(serviceProvider, typeof(TAgent), additionalArguments);
            return ValueTask.FromResult(agent);
        }
        catch (Exception e)
        {
            return ValueTask.FromException<TAgent>(e);
        }
    }

    public static ValueTask<AgentType> RegisterAgentTypeAsync<TAgent>(this IAgentRuntime runtime, AgentType type, IServiceProvider serviceProvider, params object[] additionalArguments) where TAgent : IHostableAgent
    {
        Func<ValueTask<TAgent>> factory = () => ActivateAgentAsync<TAgent>(serviceProvider, additionalArguments);
        return runtime.RegisterAgentFactoryAsync(type, factory);
    }
}

