// Copyright (c) Microsoft Corporation. All rights reserved.
// KernelPluginMiddleware.cs

using System;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading;
using System.Threading.Tasks;
using AutoGen.SemanticKernel.Extension;
using Microsoft.SemanticKernel;

namespace AutoGen.SemanticKernel;

/// <summary>
/// A middleware that consumes <see cref="KernelPlugin"/>
/// </summary>
public class KernelPluginMiddleware : IMiddleware
{
    private readonly KernelPlugin _kernelPlugin;
    private readonly FunctionCallMiddleware _functionCallMiddleware;
    public string? Name => nameof(KernelPluginMiddleware);

    public KernelPluginMiddleware(Kernel kernel, KernelPlugin kernelPlugin)
    {
        _kernelPlugin = kernelPlugin;
        var functionContracts = kernelPlugin.Select(k => k.Metadata.ToFunctionContract());
        var functionMap = kernelPlugin.ToDictionary(kv => kv.Metadata.Name, kv => InvokeFunctionPartial(kernel, kv));
        _functionCallMiddleware = new FunctionCallMiddleware(functionContracts, functionMap, Name);
    }

    public Task<IMessage> InvokeAsync(MiddlewareContext context, IAgent agent, CancellationToken cancellationToken = default)
    {
        return _functionCallMiddleware.InvokeAsync(context, agent, cancellationToken);
    }

    private async Task<string> InvokeFunctionAsync(Kernel kernel, KernelFunction function, string arguments)
    {
        var kernelArguments = new KernelArguments();
        var parameters = function.Metadata.Parameters;
        var jsonObject = JsonSerializer.Deserialize<JsonObject>(arguments) ?? new JsonObject();
        foreach (var parameter in parameters)
        {
            var parameterName = parameter.Name;
            if (jsonObject.ContainsKey(parameterName))
            {
                var parameterType = parameter.ParameterType ?? throw new ArgumentException($"Missing parameter type for {parameterName}");
                var parameterValue = jsonObject[parameterName];
                var parameterObject = parameterValue.Deserialize(parameterType);
                kernelArguments.Add(parameterName, parameterObject);
            }
            else
            {
                if (parameter.DefaultValue != null)
                {
                    kernelArguments.Add(parameterName, parameter.DefaultValue);
                }
                else if (parameter.IsRequired)
                {
                    throw new ArgumentException($"Missing required parameter: {parameterName}");
                }
            }
        }
        var result = await function.InvokeAsync(kernel, kernelArguments);

        return result.ToString();
    }

    private Func<string, Task<string>> InvokeFunctionPartial(Kernel kernel, KernelFunction function)
    {
        return async (string args) =>
        {
            var result = await InvokeFunctionAsync(kernel, function, args);
            return result.ToString();
        };
    }
}
