// Copyright (c) 2023 - 2024, Owners of https://github.com/autogenhub
// SPDX-License-Identifier: Apache-2.0
// Contributions to this project, i.e., https://github.com/autogenhub/autogen, 
// are licensed under the Apache License, Version 2.0 (Apache-2.0).
// Portions derived from  https://github.com/microsoft/autogen under the MIT License.
// SPDX-License-Identifier: MIT
// Copyright (c) Microsoft Corporation. All rights reserved.
// KernelExtension.cs

using Microsoft.DotNet.Interactive;
using Microsoft.DotNet.Interactive.Commands;
using Microsoft.DotNet.Interactive.Connection;
using Microsoft.DotNet.Interactive.Events;

namespace AutoGen.DotnetInteractive.Extension;

public static class KernelExtension
{
    public static async Task<string?> RunSubmitCodeCommandAsync(
        this Kernel kernel,
        string codeBlock,
        string targetKernelName,
        CancellationToken ct = default)
    {
        try
        {
            var cmd = new SubmitCode(codeBlock, targetKernelName);
            var res = await kernel.SendAndThrowOnCommandFailedAsync(cmd, ct);
            var events = res.Events;
            var displayValues = res.Events.Where(x => x is StandardErrorValueProduced || x is StandardOutputValueProduced || x is ReturnValueProduced || x is DisplayedValueProduced)
                    .SelectMany(x => (x as DisplayEvent)!.FormattedValues);

            if (displayValues is null || displayValues.Count() == 0)
            {
                return null;
            }

            return string.Join("\n", displayValues.Select(x => x.Value));
        }
        catch (Exception ex)
        {
            return $"Error: {ex.Message}";
        }
    }

    internal static void SetUpValueSharingIfSupported(this ProxyKernel proxyKernel)
    {
        var supportedCommands = proxyKernel.KernelInfo.SupportedKernelCommands;
        if (supportedCommands.Any(d => d.Name == nameof(RequestValue)) &&
            supportedCommands.Any(d => d.Name == nameof(SendValue)))
        {
            proxyKernel.UseValueSharing();
        }
    }

    internal static async Task<KernelCommandResult> SendAndThrowOnCommandFailedAsync(
        this Kernel kernel,
        KernelCommand command,
        CancellationToken cancellationToken)
    {
        var result = await kernel.SendAsync(command, cancellationToken);
        result.ThrowOnCommandFailed();
        return result;
    }

    internal static void ThrowOnCommandFailed(this KernelCommandResult result)
    {
        var failedEvents = result.Events.OfType<CommandFailed>();
        if (!failedEvents.Any())
        {
            return;
        }

        if (failedEvents.Skip(1).Any())
        {
            var innerExceptions = failedEvents.Select(f => f.GetException());
            throw new AggregateException(innerExceptions);
        }
        else
        {
            throw failedEvents.Single().GetException();
        }
    }

    private static Exception GetException(this CommandFailed commandFailedEvent)
        => new Exception(commandFailedEvent.Message);
}
